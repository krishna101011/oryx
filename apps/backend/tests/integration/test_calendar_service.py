"""Phase 5 Wave E — calendar service (schedule / cancel CRUD + draft-status).

Real Postgres. Asserts the mandatory guarantees:
  - schedule rejected from a non-approved/non-scheduled draft status
  - schedule rejected for an inactive target
  - schedule rejected for a past scheduled_at
  - duplicate-target scheduling surfaces a clean error (not a raw DB exception)
  - first entry promotes draft approved → scheduled
  - second target while already 'scheduled' does NOT change status further
  - cancel reverts to approved ONLY when it was the last scheduled entry
    (both branches: reverts, and does NOT revert when siblings remain)
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


async def _seed_approved_draft(sm):
    """account → workspace → research ws → packet → approved draft (v1)."""
    from oryx.core.models import (
        Account,
        ContentDraft,
        DraftVersion,
        ResearchPacket,
        ResearchWorkspace,
        Workspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"cal+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="W", owner_account_id=account.id)
        session.add(ws)
        await session.flush()
        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account.id, workspace_id=ws.id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws.id,
            name="P",
            status="consumed",
            intelligence_object_ids=[],
            conflict_acknowledged_ids=[],
            ready_at=now,
        )
        session.add(packet)
        await session.flush()
        draft = ContentDraft(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            account_id=account.id,
            packet_id=packet.id,
            format="article",
            title="Schedulable Draft",
            status="approved",
            current_version=1,
            generation_model="claude-sonnet-4-6",
            generation_version=1,
            word_count=3,
        )
        session.add(draft)
        await session.flush()
        session.add(
            DraftVersion(
                id=uuid.uuid4(),
                draft_id=draft.id,
                version_number=1,
                content="The body content.",
                edited_by=account.id,
                is_ai_generated=True,
                word_count=3,
            )
        )
        await session.commit()
        return ws.id, account.id, draft.id


async def _make_target(sm, *, workspace_id, channel="webhook", name="T", active=True):
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import PublishTarget

    ct, iv = encrypt_credentials({"secret": "s"})
    async with sm() as session:
        target = PublishTarget(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            channel=channel,
            credentials=ct,
            credentials_iv=iv,
            config={},
            is_active=active,
        )
        session.add(target)
        await session.commit()
        return target.id


def _future(minutes=60):
    return datetime.now(UTC) + timedelta(minutes=minutes)


async def _draft_status(sm, draft_id):
    from oryx.core.models import ContentDraft

    async with sm() as session:
        draft = await session.get(ContentDraft, draft_id)
        return draft.status


# --------------------------------------------------------------------------- #
# schedule_draft — guards
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_schedule_rejected_from_non_schedulable_status(sm) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.core.models import ContentDraft
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    async with sm() as session:
        draft = await session.get(ContentDraft, draft_id)
        draft.status = "draft"
        await session.commit()

    with pytest.raises(PreconditionFailedError):
        await CalendarService(sm).schedule_draft(
            draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
            account_id=account_id, workspace_id=ws_id,
        )


@pytest.mark.asyncio
async def test_schedule_rejected_for_inactive_target(sm) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, active=False)

    with pytest.raises(PreconditionFailedError):
        await CalendarService(sm).schedule_draft(
            draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
            account_id=account_id, workspace_id=ws_id,
        )


@pytest.mark.asyncio
async def test_schedule_rejected_for_past_time(sm) -> None:
    from oryx.core.errors import BadRequestError
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)

    with pytest.raises(BadRequestError):
        await CalendarService(sm).schedule_draft(
            draft_id=draft_id, target_id=target_id,
            scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
            account_id=account_id, workspace_id=ws_id,
        )


@pytest.mark.asyncio
async def test_duplicate_target_surfaces_clean_error(sm) -> None:
    """Re-scheduling the SAME target for a draft raises a clean
    PreconditionFailedError, not a raw IntegrityError from the unique index."""
    from oryx.core.errors import PreconditionFailedError
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    svc = CalendarService(sm)

    await svc.schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    with pytest.raises(PreconditionFailedError):
        await svc.schedule_draft(
            draft_id=draft_id, target_id=target_id, scheduled_at=_future(120),
            account_id=account_id, workspace_id=ws_id,
        )


# --------------------------------------------------------------------------- #
# schedule_draft — draft status interaction
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_first_entry_promotes_approved_to_scheduled(sm) -> None:
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)

    entry = await CalendarService(sm).schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    assert entry.status == "scheduled"
    assert await _draft_status(sm, draft_id) == "scheduled"


@pytest.mark.asyncio
async def test_second_target_does_not_change_status_further(sm) -> None:
    """Scheduling a SECOND target while the draft is already 'scheduled' keeps it
    'scheduled' — an explicit non-regression assertion."""
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    t1 = await _make_target(sm, workspace_id=ws_id, channel="webhook", name="A")
    t2 = await _make_target(sm, workspace_id=ws_id, channel="notion", name="B")
    svc = CalendarService(sm)

    await svc.schedule_draft(
        draft_id=draft_id, target_id=t1, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    assert await _draft_status(sm, draft_id) == "scheduled"
    await svc.schedule_draft(
        draft_id=draft_id, target_id=t2, scheduled_at=_future(120),
        account_id=account_id, workspace_id=ws_id,
    )
    assert await _draft_status(sm, draft_id) == "scheduled"


# --------------------------------------------------------------------------- #
# cancel_entry — revert logic (both branches)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_cancel_last_entry_reverts_draft_to_approved(sm) -> None:
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    svc = CalendarService(sm)

    entry = await svc.schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    assert await _draft_status(sm, draft_id) == "scheduled"

    cancelled = await svc.cancel_entry(
        entry_id=entry.id, account_id=account_id, workspace_id=ws_id
    )
    assert cancelled.status == "cancelled"
    # last scheduled entry gone → draft reverts.
    assert await _draft_status(sm, draft_id) == "approved"


@pytest.mark.asyncio
async def test_cancel_does_not_revert_when_siblings_remain(sm) -> None:
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    t1 = await _make_target(sm, workspace_id=ws_id, channel="webhook", name="A")
    t2 = await _make_target(sm, workspace_id=ws_id, channel="notion", name="B")
    svc = CalendarService(sm)

    e1 = await svc.schedule_draft(
        draft_id=draft_id, target_id=t1, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    await svc.schedule_draft(
        draft_id=draft_id, target_id=t2, scheduled_at=_future(120),
        account_id=account_id, workspace_id=ws_id,
    )

    # Cancel one of two — a sibling remains scheduled → no revert.
    await svc.cancel_entry(
        entry_id=e1.id, account_id=account_id, workspace_id=ws_id
    )
    assert await _draft_status(sm, draft_id) == "scheduled"


@pytest.mark.asyncio
async def test_cancel_non_scheduled_entry_rejected(sm) -> None:
    from oryx.core.errors import PreconditionFailedError
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    svc = CalendarService(sm)

    entry = await svc.schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    await svc.cancel_entry(
        entry_id=entry.id, account_id=account_id, workspace_id=ws_id
    )
    # second cancel hits a 'cancelled' (non-scheduled) entry → rejected.
    with pytest.raises(PreconditionFailedError):
        await svc.cancel_entry(
            entry_id=entry.id, account_id=account_id, workspace_id=ws_id
        )


@pytest.mark.asyncio
async def test_schedule_emits_event(sm) -> None:
    from oryx.core.models import OutboxEvent
    from oryx.services.calendar.events.constants import CALENDAR_ENTRY_SCHEDULED
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)

    await CalendarService(sm).schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    async with sm() as session:
        ev = (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.event_name == CALENDAR_ENTRY_SCHEDULED)
                .order_by(OutboxEvent.created_at.desc())
            )
        ).scalars().first()
        assert ev is not None
        assert ev.event["payload"]["draftId"] == str(draft_id)


@pytest.mark.asyncio
async def test_cancel_emits_event(sm) -> None:
    from oryx.core.models import OutboxEvent
    from oryx.services.calendar.events.constants import CALENDAR_ENTRY_CANCELLED
    from oryx.services.calendar.service import CalendarService

    ws_id, account_id, draft_id = await _seed_approved_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id)
    svc = CalendarService(sm)
    entry = await svc.schedule_draft(
        draft_id=draft_id, target_id=target_id, scheduled_at=_future(),
        account_id=account_id, workspace_id=ws_id,
    )
    await svc.cancel_entry(
        entry_id=entry.id, account_id=account_id, workspace_id=ws_id
    )
    async with sm() as session:
        ev = (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.event_name == CALENDAR_ENTRY_CANCELLED)
                .order_by(OutboxEvent.created_at.desc())
            )
        ).scalars().first()
        assert ev is not None
        assert ev.event["payload"]["calendarEntryId"] == str(entry.id)
