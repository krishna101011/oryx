"""Phase 5 Wave B — template pipeline integration tests.

Exercises:
  - Default template seeding (lazy on list call)
  - Template CRUD (create, read, update, delete non-default)
  - Default template cannot be deleted
  - resolve_template with explicit template_id
  - resolve_template falls back to default
  - Draft generation with template wired through (generator faked)
  - Concurrent seeding — no duplicate defaults (DB constraint)
  - is_default PATCH guard → BadRequestError
  - switch_format on approved draft → PreconditionFailedError (HTTP 409)
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import update

pytestmark = pytest.mark.requires_db


class _FakeGenerator:
    model = "claude-sonnet-4-6"
    version = 1
    calls = 0
    last_template = None

    async def generate(self, *, objects, format, instructions=None, template=None):
        from oryx.services.drafts.models import GeneratedDraft
        self.calls += 1
        self.last_template = template
        return GeneratedDraft(
            content="Acme raised five billion dollars",
            word_count=5,
            token_count=42,
        )


async def _seed_workspace(sm):
    """Minimal account + workspace for template tests."""
    from oryx.core.models import Account, Workspace

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"t+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="TemplateTest", owner_account_id=account.id)
        session.add(ws)
        await session.commit()
        return ws.id, account.id


async def _seed_packet(sm, *, ws_id: uuid.UUID, account_id: uuid.UUID):
    from oryx.core.models import (
        IntakeItem,
        IntakeSource,
        IntelligenceObject,
        ResearchPacket,
        ResearchWorkspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()
        item = IntakeItem(
            id=uuid.uuid4(),
            workspace_id=ws_id,
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
            workspace_id=ws_id,
            intake_item_id=item.id,
            epistemic_type="fact",
            confidence_score=0.9,
            verification_status="verified",
            claim_ids=[],
            conflict_ids=[],
            key_facts={"Subj": {"predicate": "raised", "object": "$5B"}},
            headline="Headline A",
            scoring_version=1,
        )
        session.add(obj)
        await session.flush()
        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account_id, workspace_id=ws_id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws_id,
            name="Template Packet",
            status="ready",
            intelligence_object_ids=[obj.id],
            conflict_acknowledged_ids=[],
            ready_at=now,
        )
        session.add(packet)
        await session.commit()
        return packet.id


@pytest.mark.asyncio
async def test_list_templates_seeds_defaults(sm) -> None:
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        templates = await svc.list_templates(ws_id, session=session)
        await session.commit()

    assert len(templates) == 6
    formats = {t.format for t in templates}
    assert formats == {
        "tweet_thread", "linkedin_post", "newsletter_section",
        "article", "report_summary", "custom",
    }
    assert all(t.is_default for t in templates)


@pytest.mark.asyncio
async def test_list_templates_idempotent(sm) -> None:
    """Calling list_templates twice does not duplicate defaults."""
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        await svc.list_templates(ws_id, session=session)
        await session.commit()
    async with sm() as session:
        templates = await svc.list_templates(ws_id, session=session)
        await session.commit()

    assert len(templates) == 6


@pytest.mark.asyncio
async def test_create_and_get_template(sm) -> None:
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        t = await svc.create_template(
            ws_id,
            name="My Tweet Style",
            format="tweet_thread",
            tone="conversational",
            max_words=None,
            min_words=None,
            structure_hint="Each tweet ends with a hook.",
            session=session,
        )
        await session.commit()

    assert t.name == "My Tweet Style"
    assert t.is_default is False

    async with sm() as session:
        fetched = await svc.get_template(t.id, ws_id, session=session)

    assert fetched.id == t.id
    assert fetched.structure_hint == "Each tweet ends with a hook."


@pytest.mark.asyncio
async def test_delete_non_default_template(sm) -> None:
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        t = await svc.create_template(
            ws_id,
            name="Temp",
            format="article",
            tone="formal",
            max_words=None,
            min_words=None,
            structure_hint=None,
            session=session,
        )
        await session.commit()

    async with sm() as session:
        await svc.delete_template(t.id, ws_id, session=session)
        await session.commit()

    from oryx.core.errors import NotFoundError
    with pytest.raises(NotFoundError):
        async with sm() as session:
            await svc.get_template(t.id, ws_id, session=session)


@pytest.mark.asyncio
async def test_delete_default_template_raises(sm) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        templates = await svc.list_templates(ws_id, session=session)
        await session.commit()

    default = next(t for t in templates if t.is_default)
    with pytest.raises(PreconditionFailedError):
        async with sm() as session:
            await svc.delete_template(default.id, ws_id, session=session)


@pytest.mark.asyncio
async def test_resolve_template_returns_default_when_no_id(sm) -> None:
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        template = await svc.resolve_template(ws_id, "article", None, session)

    assert template.format == "article"
    assert template.is_default is True


@pytest.mark.asyncio
async def test_resolve_explicit_template_id(sm) -> None:
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        custom = await svc.create_template(
            ws_id,
            name="My Article",
            format="article",
            tone="formal",
            max_words=2000,
            min_words=500,
            structure_hint=None,
            session=session,
        )
        await session.commit()

    async with sm() as session:
        resolved = await svc.resolve_template(ws_id, "article", custom.id, session)

    assert resolved.id == custom.id
    assert resolved.max_words == 2000


@pytest.mark.asyncio
async def test_generate_draft_with_template(sm) -> None:
    """End-to-end: generate_draft resolves and passes a ContentTemplate to the generator."""
    from oryx.services.drafts.service import DraftService
    from oryx.services.templates.service import TemplateService

    ws_id, account_id = await _seed_workspace(sm)
    packet_id = await _seed_packet(sm, ws_id=ws_id, account_id=account_id)

    fake_gen = _FakeGenerator()
    svc = DraftService(
        sm,
        generator=fake_gen,  # type: ignore[arg-type]
        template_service=TemplateService(sm),
    )

    draft = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )

    assert draft.format == "article"
    assert fake_gen.calls == 1
    # The template was passed to the generator (not None).
    assert fake_gen.last_template is not None
    assert fake_gen.last_template.format == "article"
    assert fake_gen.last_template.is_default is True


@pytest.mark.asyncio
async def test_concurrent_seeding_no_duplicate_defaults(sm) -> None:
    """Concurrent ensure_default_templates calls must not produce duplicate
    defaults. The partial UNIQUE index (workspace_id, format) WHERE is_default=TRUE
    is the DB-layer guarantee; this test exercises it with two sequential calls
    in separate sessions (mimicking the race scenario the constraint handles)."""
    from sqlalchemy import func, select

    from oryx.core.models import ContentTemplate as ContentTemplateRow
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    # Two concurrent ensure_default_templates calls — asyncio.gather runs them
    # both; the second hits ON CONFLICT DO NOTHING on each insert.
    async def seed():
        async with sm() as session:
            await svc.ensure_default_templates(ws_id, session)
            await session.commit()

    await asyncio.gather(seed(), seed())

    async with sm() as session:
        for fmt in ("tweet_thread", "linkedin_post", "newsletter_section",
                    "article", "report_summary", "custom"):
            count = (await session.execute(
                select(func.count(ContentTemplateRow.id)).where(
                    ContentTemplateRow.workspace_id == ws_id,
                    ContentTemplateRow.format == fmt,
                    ContentTemplateRow.is_default.is_(True),
                )
            )).scalar_one()
            assert count == 1, f"Expected 1 default for {fmt}, got {count}"


@pytest.mark.asyncio
async def test_patch_is_default_rejected(sm) -> None:
    """PATCH with is_default in the body raises BadRequestError (HTTP 400)."""
    from oryx.core.errors import BadRequestError
    from oryx.services.templates.service import TemplateService

    ws_id, _ = await _seed_workspace(sm)
    svc = TemplateService(sm)

    async with sm() as session:
        t = await svc.create_template(
            ws_id,
            name="Guard Test",
            format="article",
            tone="formal",
            max_words=None,
            min_words=None,
            structure_hint=None,
            session=session,
        )
        await session.commit()

    with pytest.raises(BadRequestError):
        async with sm() as session:
            await svc.update_template(
                t.id,
                ws_id,
                is_default_attempted=True,
                session=session,
            )


@pytest.mark.asyncio
async def test_switch_format_approved_draft_rejected(sm) -> None:
    """switch_format on an approved draft raises PreconditionFailedError (HTTP 409)."""
    from oryx.core.errors import PreconditionFailedError
    from oryx.core.models import ContentDraft
    from oryx.services.drafts.service import DraftService
    from oryx.services.templates.service import TemplateService

    ws_id, account_id = await _seed_workspace(sm)
    packet_id = await _seed_packet(sm, ws_id=ws_id, account_id=account_id)

    fake_gen = _FakeGenerator()
    svc = DraftService(sm, generator=fake_gen, template_service=TemplateService(sm))  # type: ignore[arg-type]

    draft = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )

    # Directly set status to 'approved' — the only path that matters for the guard.
    async with sm() as session:
        await session.execute(
            update(ContentDraft)
            .where(ContentDraft.id == draft.id)
            .values(status="approved")
        )
        await session.commit()

    with pytest.raises(PreconditionFailedError):
        await svc.switch_format(
            draft_id=draft.id,
            new_format="linkedin_post",
            template_id=None,
            workspace_id=ws_id,
            account_id=account_id,
        )
