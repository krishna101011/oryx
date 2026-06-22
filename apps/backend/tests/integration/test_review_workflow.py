"""Phase 5 Wave C — review workflow + approval, end-to-end against Postgres.

Exercises every mandatory guard:
  - submit_review only from 'draft'
  - approve self-account blocked under balanced/strict, allowed under loose,
    allowed for platform admin regardless of policy
  - reject / request-changes require a non-empty note (400)
  - reject / request-changes have NO self-account restriction
  - edit (save_version) and switch_format during changes_requested auto-revert
    the draft to 'draft'
  - the full resubmission loop, and the approved← causation chain + events

The Sonnet call is faked (everything else real), mirroring the Wave A pipeline
test's _FakeGenerator + _seed_packet conventions.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from oryx.core.errors import BadRequestError, NotFoundError, PreconditionFailedError
from oryx.services.drafts.events.constants import (
    DRAFT_APPROVED,
    DRAFT_CREATED,
    DRAFT_REJECTED,
    DRAFT_UPDATED,
)
from oryx.services.drafts.service import DraftService

pytestmark = pytest.mark.requires_db


class _FakeGenerator:
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


async def _latest_event_row(session, name: str, draft_id):
    from oryx.core.models import OutboxEvent

    rows = (
        await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.event_name == name)
            .order_by(OutboxEvent.created_at.desc())
        )
    ).scalars().all()
    for r in rows:
        if r.event["payload"].get("draftId") == str(draft_id):
            return r
    return None


async def _seed_packet(sm, *, status: str = "ready", with_objects: int = 2):
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


async def _make_draft(sm, *, gen=None):
    """Seed a packet and generate a fresh draft (status='draft')."""
    ws_id, account_id, packet_id, _ = await _seed_packet(sm)
    svc = DraftService(sm, generator=gen or _FakeGenerator())
    draft = await svc.generate_draft(
        packet_id=packet_id,
        format="article",
        instructions=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    return svc, ws_id, account_id, draft


async def _make_second_account(sm) -> uuid.UUID:
    from oryx.core.models import Account

    async with sm() as session:
        acc = Account(
            id=uuid.uuid4(),
            email=f"r+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(acc)
        await session.commit()
        return acc.id


async def _set_strictness(sm, account_id: uuid.UUID, value: str) -> None:
    from oryx.core.models import Preferences

    async with sm() as session:
        session.add(Preferences(account_id=account_id, verification_strictness=value))
        await session.commit()


async def _set_platform_admin(sm, account_id: uuid.UUID) -> None:
    from oryx.core.models import Account

    async with sm() as session:
        acc = await session.get(Account, account_id)
        acc.is_platform_admin = True
        await session.commit()


async def _status(sm, draft_id) -> str:
    from oryx.core.models import ContentDraft

    async with sm() as session:
        return (await session.get(ContentDraft, draft_id)).status


# ---------------- submit_review state guard ----------------


@pytest.mark.asyncio
async def test_submit_review_from_draft_enters_in_review(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    out = await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    assert out.status == "in_review"
    async with sm() as session:
        ev = await _latest_event_row(session, DRAFT_UPDATED, draft.id)
        assert ev is not None  # reuses DRAFT_UPDATED, no new event
        assert ev.event["payload"]["statusChange"] == "in_review"


@pytest.mark.asyncio
async def test_submit_review_rejected_from_non_draft_status(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )  # now in_review
    with pytest.raises(PreconditionFailedError):
        await svc.submit_review(
            draft_id=draft.id, account_id=account_id, workspace_id=ws_id
        )


# ---------------- approve self-account policy ----------------


@pytest.mark.asyncio
async def test_approve_same_account_blocked_under_balanced(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    # No preferences row → defaults to 'balanced' → self-approval blocked.
    with pytest.raises(PreconditionFailedError):
        await svc.approve_draft(
            draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note=None
        )
    assert await _status(sm, draft.id) == "in_review"  # unchanged


@pytest.mark.asyncio
async def test_approve_same_account_blocked_under_strict(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await _set_strictness(sm, account_id, "strict")
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    with pytest.raises(PreconditionFailedError):
        await svc.approve_draft(
            draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note=None
        )


@pytest.mark.asyncio
async def test_approve_same_account_allowed_under_loose(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await _set_strictness(sm, account_id, "loose")
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    out = await svc.approve_draft(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note=None
    )
    assert out.status == "approved"


@pytest.mark.asyncio
async def test_approve_same_account_allowed_for_platform_admin(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    # Strict policy AND platform admin — admin override wins.
    await _set_strictness(sm, account_id, "strict")
    await _set_platform_admin(sm, account_id)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    out = await svc.approve_draft(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note=None
    )
    assert out.status == "approved"


@pytest.mark.asyncio
async def test_approve_different_account_allowed_and_chains_causation(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    reviewer = await _make_second_account(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    out = await svc.approve_draft(
        draft_id=draft.id,
        account_id=reviewer,
        workspace_id=ws_id,
        note="ship it",
    )
    assert out.status == "approved"

    from oryx.core.models import DraftReview

    async with sm() as session:
        review = (
            await session.execute(
                select(DraftReview).where(DraftReview.draft_id == draft.id)
            )
        ).scalar_one()
        assert review.outcome == "approved"
        assert review.note == "ship it"
        assert review.account_id == reviewer
        assert review.version_number == out.current_version

        approved_ev = await _latest_event_row(session, DRAFT_APPROVED, draft.id)
        assert approved_ev is not None
        # causation parent = the most recent updated event (submit-review),
        # else created — never null for an approved draft.
        updated_ev = await _latest_event_row(session, DRAFT_UPDATED, draft.id)
        created_ev = await _latest_event_row(session, DRAFT_CREATED, draft.id)
        expected = (updated_ev or created_ev).event["id"]
        assert approved_ev.event["causationId"] == expected


# ---------------- reject / request-changes note + no self restriction ----------------


@pytest.mark.asyncio
async def test_reject_requires_non_empty_note(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    with pytest.raises(BadRequestError):
        await svc.reject_draft(
            draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note="   "
        )


@pytest.mark.asyncio
async def test_request_changes_requires_non_empty_note(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    with pytest.raises(BadRequestError):
        await svc.request_changes(
            draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note=""
        )


@pytest.mark.asyncio
async def test_reject_has_no_self_account_restriction(sm) -> None:
    # Same account that created the draft CAN reject it (no rubber-stamp risk).
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    out = await svc.reject_draft(
        draft_id=draft.id,
        account_id=account_id,
        workspace_id=ws_id,
        note="off-topic",
    )
    assert out.status == "rejected"
    async with sm() as session:
        ev = await _latest_event_row(session, DRAFT_REJECTED, draft.id)
        assert ev is not None
        assert ev.event["payload"]["reason"] == "off-topic"


@pytest.mark.asyncio
async def test_request_changes_has_no_self_account_restriction(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    out = await svc.request_changes(
        draft_id=draft.id,
        account_id=account_id,
        workspace_id=ws_id,
        note="tighten the lede",
    )
    assert out.status == "changes_requested"


# ---------------- changes_requested auto-revert ----------------


@pytest.mark.asyncio
async def test_edit_during_changes_requested_reverts_to_draft(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    await svc.request_changes(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note="redo"
    )
    assert await _status(sm, draft.id) == "changes_requested"

    out = await svc.save_version(
        draft_id=draft.id,
        content="analyst reworked the body",
        content_html=None,
        edit_note="addressed feedback",
        account_id=account_id,
        workspace_id=ws_id,
    )
    assert out.status == "draft"  # auto-reverted by the same edit transaction


@pytest.mark.asyncio
async def test_save_version_on_plain_draft_keeps_draft_status(sm) -> None:
    # Guards against over-reach: a normal edit does not move status around.
    svc, ws_id, account_id, draft = await _make_draft(sm)
    out = await svc.save_version(
        draft_id=draft.id,
        content="just an edit",
        content_html=None,
        edit_note=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    assert out.status == "draft"


@pytest.mark.asyncio
async def test_switch_format_during_changes_requested_reverts_to_draft(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    await svc.request_changes(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id, note="wrong format"
    )
    assert await _status(sm, draft.id) == "changes_requested"

    out = await svc.switch_format(
        draft_id=draft.id,
        new_format="tweet_thread",
        template_id=None,
        workspace_id=ws_id,
        account_id=account_id,
    )
    assert out.status == "draft"
    assert out.format == "tweet_thread"


# ---------------- review history ----------------


@pytest.mark.asyncio
async def test_list_reviews_returns_history_latest_first(sm) -> None:
    svc, ws_id, account_id, draft = await _make_draft(sm)
    reviewer = await _make_second_account(sm)
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    await svc.request_changes(
        draft_id=draft.id, account_id=reviewer, workspace_id=ws_id, note="round one"
    )
    # edit reverts to draft, then resubmit + approve
    await svc.save_version(
        draft_id=draft.id,
        content="reworked",
        content_html=None,
        edit_note=None,
        account_id=account_id,
        workspace_id=ws_id,
    )
    await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    await svc.approve_draft(
        draft_id=draft.id, account_id=reviewer, workspace_id=ws_id, note=None
    )

    reviews = await svc.list_reviews(workspace_id=ws_id, draft_id=draft.id)
    assert [r.outcome for r in reviews] == ["approved", "changes_requested"]


@pytest.mark.asyncio
async def test_list_reviews_unknown_draft_404(sm) -> None:
    svc = DraftService(sm)
    with pytest.raises(NotFoundError):
        await svc.list_reviews(workspace_id=uuid.uuid4(), draft_id=uuid.uuid4())


# ---------------- full resubmission cycle ----------------


@pytest.mark.asyncio
async def test_full_resubmission_cycle(sm) -> None:
    """draft → submit → in_review → request_changes → changes_requested →
    [edit] → draft (auto-revert) → submit → in_review → approve → approved."""
    svc, ws_id, account_id, draft = await _make_draft(sm)
    reviewer = await _make_second_account(sm)

    assert draft.status == "draft"

    out = await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    assert out.status == "in_review"

    out = await svc.request_changes(
        draft_id=draft.id,
        account_id=reviewer,
        workspace_id=ws_id,
        note="needs sources",
    )
    assert out.status == "changes_requested"

    out = await svc.save_version(
        draft_id=draft.id,
        content="now with sources",
        content_html=None,
        edit_note="added citations",
        account_id=account_id,
        workspace_id=ws_id,
    )
    assert out.status == "draft"  # the single re-entry point

    out = await svc.submit_review(
        draft_id=draft.id, account_id=account_id, workspace_id=ws_id
    )
    assert out.status == "in_review"

    out = await svc.approve_draft(
        draft_id=draft.id,
        account_id=reviewer,
        workspace_id=ws_id,
        note="approved on round two",
    )
    assert out.status == "approved"

    from oryx.core.models import DraftReview

    async with sm() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(DraftReview)
                .where(DraftReview.draft_id == draft.id)
            )
        ).scalar_one()
        assert count == 2  # one changes_requested + one approved
