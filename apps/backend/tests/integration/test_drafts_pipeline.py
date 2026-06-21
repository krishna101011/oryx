"""Phase 5 Wave A — drafts service: consumption, generation, idempotency, versions.

Exercises the five invariants end-to-end against Postgres with the Sonnet call
faked (everything else real):
  #1 generation records the Sonnet model
  #2 PacketConsumerHandler sets consumed_at ONLY (no auto-generation)
  #3 one draft per packet (generate is idempotent)
  #4 append-only versions (generate / regenerate / save never overwrite)
  #5 (covered by tests/unit/test_draft_generator.py)
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


class _FakeGenerator:
    """Stands in for the Sonnet call. Reports the real model id so the
    generation_model assertion is meaningful."""

    model = "claude-sonnet-4-6"
    version = 1

    def __init__(self, text: str = "Acme raised five billion dollars", tokens: int = 42):
        self._text = text
        self._tokens = tokens
        self.calls = 0

    async def generate(self, *, objects, format, instructions=None, template=None):
        from oryx.services.drafts.models import GeneratedDraft

        self.calls += 1
        return GeneratedDraft(
            content=self._text,
            word_count=len(self._text.split()),
            token_count=self._tokens,
        )


async def _latest_event(session, name: str):
    from oryx.core.models import OutboxEvent

    rows = (
        await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.event_name == name)
            .order_by(OutboxEvent.created_at.desc())
        )
    ).scalars().all()
    return rows[0].event if rows else None


async def _seed_packet(sm, *, status: str = "ready", with_objects: int = 2):
    """account + workspace + source + N (item, intelligence_object) + research
    workspace + a packet referencing those objects."""
    from oryx.core.models import (
        Account,
        IntakeItem,
        IntakeSource,
        IntelligenceObject,
        ResearchPacket,
        ResearchWorkspace,
        Workspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"d+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="W", owner_account_id=account.id)
        session.add(ws)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()

        obj_ids: list[uuid.UUID] = []
        for i in range(with_objects):
            item = IntakeItem(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                intake_source_id=source.id,
                provider_name="rss",
                external_id=f"x-{uuid.uuid4().hex[:8]}",
                received_at=now,
                payload={},
                fingerprint=uuid.uuid4().hex,
            )
            session.add(item)
            await session.flush()
            obj = IntelligenceObject(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                intake_item_id=item.id,
                epistemic_type="fact",
                confidence_score=0.9,
                verification_status="verified",
                claim_ids=[],
                conflict_ids=[],
                key_facts={"Subj": {"predicate": "raised", "object": "$5B"}},
                headline=f"Headline {i}",
                scoring_version=1,
            )
            session.add(obj)
            await session.flush()
            obj_ids.append(obj.id)

        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account.id, workspace_id=ws.id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws.id,
            name="Packet One",
            status=status,
            intelligence_object_ids=obj_ids,
            conflict_acknowledged_ids=[],
            ready_at=now if status in ("ready", "consumed") else None,
        )
        session.add(packet)
        await session.commit()
        return ws.id, account.id, packet.id, obj_ids


@pytest.mark.asyncio
async def test_packet_consumer_sets_consumed_at_only(sm) -> None:
    from oryx.core.models import ContentDraft, ResearchPacket
    from oryx.services.drafts.service import DraftService

    ws_id, _account_id, packet_id, _ = await _seed_packet(sm, status="ready")

    await DraftService(sm).consume_packet(workspace_id=ws_id, packet_id=packet_id)

    async with sm() as session:
        packet = await session.get(ResearchPacket, packet_id)
        assert packet.consumed_at is not None  # handoff marked
        assert packet.status == "ready"  # invariant #2: status NOT changed
        draft_count = (
            await session.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(ContentDraft.packet_id == packet_id)
            )
        ).scalar_one()
        assert draft_count == 0  # invariant #2: NO auto-generation


@pytest.mark.asyncio
async def test_consume_packet_idempotent(sm) -> None:
    from oryx.core.models import ResearchPacket
    from oryx.services.drafts.service import DraftService

    ws_id, _account_id, packet_id, _ = await _seed_packet(sm)
    svc = DraftService(sm)

    await svc.consume_packet(workspace_id=ws_id, packet_id=packet_id)
    async with sm() as session:
        first = (await session.get(ResearchPacket, packet_id)).consumed_at
    await svc.consume_packet(workspace_id=ws_id, packet_id=packet_id)
    async with sm() as session:
        second = (await session.get(ResearchPacket, packet_id)).consumed_at
    assert first == second  # not re-stamped on re-delivery


@pytest.mark.asyncio
async def test_generate_creates_draft_version_and_citations(sm) -> None:
    from oryx.core.models import (
        ContentDraft,
        DraftCitation,
        DraftVersion,
        ResearchPacket,
    )
    from oryx.services.drafts.events.constants import DRAFT_CREATED
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, obj_ids = await _seed_packet(sm, with_objects=2)
    gen = _FakeGenerator(text="Acme raised five billion dollars", tokens=42)

    draft = await DraftService(sm, generator=gen).generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )

    async with sm() as session:
        row = await session.get(ContentDraft, draft.id)
        assert row.generation_model == "claude-sonnet-4-6"  # invariant #1
        assert row.current_version == 1
        assert row.word_count == 5

        versions = (
            await session.execute(
                select(DraftVersion).where(DraftVersion.draft_id == draft.id)
            )
        ).scalars().all()
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].is_ai_generated is True
        assert versions[0].token_count == 42

        cites = (
            await session.execute(
                select(DraftCitation.intelligence_object_id).where(
                    DraftCitation.draft_id == draft.id
                )
            )
        ).scalars().all()
        assert set(cites) == set(obj_ids)  # provenance for every source object

        packet = await session.get(ResearchPacket, packet_id)
        assert packet.consumed_at is not None

        ev = await _latest_event(session, DRAFT_CREATED)
        assert ev is not None
        assert ev["payload"]["draftId"] == str(draft.id)
        assert ev["payload"]["versionNumber"] == 1


@pytest.mark.asyncio
async def test_generate_idempotent_one_draft_per_packet(sm) -> None:
    from oryx.core.models import ContentDraft
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    gen = _FakeGenerator()
    svc = DraftService(sm, generator=gen)

    d1 = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    d2 = await svc.generate_draft(
        packet_id=packet_id,
        format="tweet_thread",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    assert d1.id == d2.id  # invariant #3: same draft returned
    assert gen.calls == 1  # second call short-circuits before the AI call

    async with sm() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(ContentDraft.packet_id == packet_id)
            )
        ).scalar_one()
        assert count == 1


@pytest.mark.asyncio
async def test_regenerate_appends_ai_version(sm) -> None:
    from oryx.core.models import ContentDraft, DraftVersion
    from oryx.services.drafts.events.constants import DRAFT_UPDATED
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    draft = await DraftService(sm, generator=_FakeGenerator(text="v1 text")).generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )

    await DraftService(sm, generator=_FakeGenerator(text="regenerated body text")).regenerate_draft(
        draft_id=draft.id,
        instructions="punchier",
        account_id=account_id,
        workspace_id=ws_id,
    )

    async with sm() as session:
        row = await session.get(ContentDraft, draft.id)
        assert row.current_version == 2
        versions = (
            await session.execute(
                select(DraftVersion)
                .where(DraftVersion.draft_id == draft.id)
                .order_by(DraftVersion.version_number)
            )
        ).scalars().all()
        assert len(versions) == 2  # append-only (invariant #4)
        assert versions[0].content == "v1 text"  # v1 NEVER overwritten
        assert versions[1].is_ai_generated is True
        ev = await _latest_event(session, DRAFT_UPDATED)
        assert ev["payload"]["versionNumber"] == 2


@pytest.mark.asyncio
async def test_save_version_appends_analyst_version(sm) -> None:
    from oryx.core.models import ContentDraft, DraftVersion
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    svc = DraftService(sm, generator=_FakeGenerator(text="ai v1"))
    draft = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )

    await svc.save_version(
        draft_id=draft.id,
        content="analyst edited body",
        content_html=None,
        edit_note="tweaks",
        account_id=account_id,
        workspace_id=ws_id,
    )

    async with sm() as session:
        row = await session.get(ContentDraft, draft.id)
        assert row.current_version == 2
        versions = (
            await session.execute(
                select(DraftVersion)
                .where(DraftVersion.draft_id == draft.id)
                .order_by(DraftVersion.version_number)
            )
        ).scalars().all()
        assert len(versions) == 2
        assert versions[1].is_ai_generated is False
        assert versions[1].content == "analyst edited body"
        assert versions[1].edit_note == "tweaks"


@pytest.mark.asyncio
async def test_save_empty_content_rejected(sm) -> None:
    from oryx.core.errors import BadRequestError
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    svc = DraftService(sm, generator=_FakeGenerator())
    draft = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    with pytest.raises(BadRequestError):
        await svc.save_version(
            draft_id=draft.id,
            content="   ",
            content_html=None,
            edit_note=None,
            account_id=account_id,
            workspace_id=ws_id,
        )


@pytest.mark.asyncio
async def test_generate_from_non_ready_packet_blocked(sm) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm, status="assembling")
    with pytest.raises(PreconditionFailedError):
        await DraftService(sm, generator=_FakeGenerator()).generate_draft(
            packet_id=packet_id,
            format="article",
            instructions=None,
            account_id=account_id,
            workspace_id=ws_id,
        )


@pytest.mark.asyncio
async def test_generate_budget_exhausted_blocks(sm) -> None:
    from oryx.core.errors import RateLimitedError
    from oryx.core.models import ContentDraft, WorkspaceAIBudget
    from oryx.services.drafts.service import DraftService

    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    async with sm() as session:
        session.add(
            WorkspaceAIBudget(
                workspace_id=ws_id,
                budget_date=datetime.now(UTC).date(),
                tokens_used=100_000,
                budget_limit=100_000,
            )
        )
        await session.commit()

    with pytest.raises(RateLimitedError):
        await DraftService(sm, generator=_FakeGenerator()).generate_draft(
            packet_id=packet_id,
            format="article",
            instructions=None,
            account_id=account_id,
            workspace_id=ws_id,
        )

    async with sm() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(ContentDraft)
                .where(ContentDraft.packet_id == packet_id)
            )
        ).scalar_one()
        assert count == 0  # no draft when budget blocks generation
