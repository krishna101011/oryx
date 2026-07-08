"""NotificationDispatcher — Phase 6 Wave A coverage.

Exercises the bus subscriber the same way test_intelligence_pipeline.py drives
ObjectConflictProjector: construct a DomainEvent, call the handler directly,
assert on the rows it committed.

The FROZEN_SECTION_2 table below is transcribed from
docs/PHASE_6_ARCHITECTURE.md §2 (Rev 2, frozen) — 14 table rows, where the
`intelligence.object.*` family row expands to 3 concrete events, so 16
event names. It is deliberately duplicated here rather than imported from
the dispatcher, so the test checks the code against the frozen document
instead of against itself.

Wave C note: every dispatch now ALSO runs the push step, which writes its own
channel='push' decision row (push_failed in these seeds — no device is ever
registered here). The assertions below therefore scope to the in_app slot via
_log_rows' channel filter; the push path has its own dedicated coverage in
test_push_delivery.py.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db

# (event name) -> (activity_type category, severity), verbatim from the frozen
# Section 2 catalog.
FROZEN_SECTION_2: dict[str, tuple[str, str]] = {
    "intake.item.received": ("system", "info"),
    "verification.conflict.detected": ("verification", "warning"),
    "verification.conflict.resolved": ("verification", "info"),
    "verification.claim.failed": ("verification", "error"),
    "verification.evidence.collected": ("verification", "info"),
    "intelligence.object.created": ("verification", "info"),
    "intelligence.object.updated": ("verification", "info"),
    "intelligence.object.reviewed": ("verification", "info"),
    "content.draft.created": ("publishing", "info"),
    "content.draft.updated": ("publishing", "info"),
    "content.draft.approved": ("publishing", "info"),
    "content.draft.rejected": ("publishing", "warning"),
    "content.draft.scheduled": ("publishing", "info"),
    "content.calendar.cancelled": ("publishing", "info"),
    "content.published": ("publishing", "info"),
    "content.publish.failed": ("publishing", "error"),
}

INTAKE_EVENT = "intake.item.received"  # category 'system' — the workhorse below


async def _seed_workspace(sm, *, members: int = 1) -> dict:
    """One workspace + N member accounts (owner first), all active members."""
    from oryx.core.models import Account, Workspace, WorkspaceMember

    now = datetime.now(UTC)
    async with sm() as session:
        accounts = []
        for _ in range(members):
            account = Account(
                id=uuid.uuid4(),
                email=f"notif+{uuid.uuid4().hex[:8]}@oryx.test",
                password_hash="x",
                password_changed_at=now,
                status="active",
            )
            session.add(account)
            accounts.append(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Notif WS", owner_account_id=accounts[0].id
        )
        session.add(workspace)
        await session.flush()
        for i, account in enumerate(accounts):
            session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    account_id=account.id,
                    role="owner" if i == 0 else "editor",
                )
            )
        await session.commit()
        return {"workspace": workspace.id, "accounts": [a.id for a in accounts]}


def _event(name: str, *, workspace_id, event_id: uuid.UUID | None = None):
    """A DomainEvent as the drainer would deliver it."""
    from oryx.services.queue.bus import DomainEvent

    now = datetime.now(UTC)
    return DomainEvent(
        id=str(event_id or uuid.uuid4()),
        name=name,
        version=1,
        occurred_at=now,
        emitted_at=now,
        workspace_id=str(workspace_id),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={"itemId": "x-1"},
    )


def _dispatcher(sm):
    from oryx.services.activity.dispatcher import NotificationDispatcher

    return NotificationDispatcher(sm)


async def _set_preference(sm, *, account_id, type_, channel="in_app", frequency="off"):
    from oryx.core.models import AlertPreference

    async with sm() as session:
        session.add(
            AlertPreference(
                account_id=account_id, type=type_, channel=channel, frequency=frequency
            )
        )
        await session.commit()


async def _inbox_rows(sm, account_id):
    from oryx.core.models import ActivityInbox

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(ActivityInbox).where(ActivityInbox.account_id == account_id)
                )
            )
            .scalars()
            .all()
        )


async def _log_rows(sm, account_id, channel: str | None = "in_app"):
    """Decision rows for one account, scoped to a channel.

    Defaults to the in_app slot: these Wave A tests assert the in_app dispatch
    decision, and since Wave C every dispatch ALSO writes a push-channel
    decision row (push_failed when no device is registered, as in these seeds).
    Pass channel='push' for the push slot, or None for every row.
    """
    from oryx.core.models import AutomationLog

    async with sm() as session:
        stmt = select(AutomationLog).where(AutomationLog.account_id == account_id)
        if channel is not None:
            stmt = stmt.where(AutomationLog.channel == channel)
        return (await session.execute(stmt)).scalars().all()


# --- Scenario 1: enabled preference -> inbox row AND notification_created log ---


@pytest.mark.asyncio
async def test_enabled_preference_creates_inbox_and_log(sm) -> None:
    """An explicit 'instant' preference produces the feed row and its decision
    log row, committed together (the log row's FK points at the inbox row)."""
    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]
    await _set_preference(sm, account_id=account, type_="system", frequency="instant")

    event = _event(INTAKE_EVENT, workspace_id=ids["workspace"])
    await _dispatcher(sm)(event)

    inbox = await _inbox_rows(sm, account)
    assert len(inbox) == 1
    row = inbox[0]
    assert row.type == "system"
    assert row.severity == "info"
    assert row.title == "New item ingested"
    assert row.workspace_id == ids["workspace"]
    assert row.data == {"itemId": "x-1"}
    assert row.source_event_type == INTAKE_EVENT
    assert row.source_event_id == uuid.UUID(event.id)
    assert row.read_at is None

    logs = await _log_rows(sm, account)
    assert len(logs) == 1
    assert logs[0].action_taken == "notification_created"
    assert logs[0].activity_inbox_id == row.id
    assert logs[0].workspace_id == ids["workspace"]
    assert logs[0].triggered_by_event_type == INTAKE_EVENT
    assert logs[0].triggered_by_event_id == uuid.UUID(event.id)


# --- Scenario 2: disabled preference -> ONLY a suppressed_by_preference log ---


@pytest.mark.asyncio
async def test_disabled_preference_writes_only_suppressed_log(sm) -> None:
    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]
    await _set_preference(sm, account_id=account, type_="system", frequency="off")

    await _dispatcher(sm)(_event(INTAKE_EVENT, workspace_id=ids["workspace"]))

    assert await _inbox_rows(sm, account) == []
    logs = await _log_rows(sm, account)
    assert len(logs) == 1
    assert logs[0].action_taken == "suppressed_by_preference"
    assert logs[0].activity_inbox_id is None


# --- Scenario 3: missing preference row -> the shared default (ENABLED) ---


@pytest.mark.asyncio
async def test_missing_preference_row_defaults_to_enabled(sm) -> None:
    """No alert_preferences row exists at all: resolve_frequency falls back to
    DEFAULT_ALERT_FREQUENCY ('instant'), which is_enabled treats as ENABLED —
    so the notification IS created."""
    from oryx.services.activity.preferences import (
        DEFAULT_ALERT_FREQUENCY,
        is_enabled,
        resolve_frequency,
    )

    assert resolve_frequency(None) == DEFAULT_ALERT_FREQUENCY == "instant"
    assert is_enabled(resolve_frequency(None)) is True  # default is ENABLED

    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]
    await _dispatcher(sm)(_event(INTAKE_EVENT, workspace_id=ids["workspace"]))

    inbox = await _inbox_rows(sm, account)
    assert len(inbox) == 1
    logs = await _log_rows(sm, account)
    assert len(logs) == 1
    assert logs[0].action_taken == "notification_created"


# --- Scenario 4: at-least-once redelivery is a no-op ---


@pytest.mark.asyncio
async def test_redelivered_event_is_noop(sm) -> None:
    """The same event id delivered twice (two distinct envelope objects, as a
    drainer retry would produce) leaves exactly one decision row and one feed
    row — the second delivery short-circuits on the existing automation_log."""
    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]
    event_id = uuid.uuid4()

    dispatcher = _dispatcher(sm)
    await dispatcher(_event(INTAKE_EVENT, workspace_id=ids["workspace"], event_id=event_id))
    await dispatcher(_event(INTAKE_EVENT, workspace_id=ids["workspace"], event_id=event_id))

    assert len(await _inbox_rows(sm, account)) == 1
    logs = await _log_rows(sm, account)
    assert len(logs) == 1
    assert logs[0].triggered_by_event_id == event_id
    # Wave C: the push decision slot is idempotent under redelivery too —
    # exactly one push row (push_failed here: no device registered).
    push_logs = await _log_rows(sm, account, channel="push")
    assert len(push_logs) == 1


# --- Scenario 5: multi-account fan-out with independent preferences ---


@pytest.mark.asyncio
async def test_multi_account_fanout_independent_preferences(sm) -> None:
    """Two workspace members, one event: the member with an 'off' preference is
    suppressed, the other gets the notification — one decision row each."""
    ids = await _seed_workspace(sm, members=2)
    account_a, account_b = ids["accounts"]
    await _set_preference(sm, account_id=account_b, type_="system", frequency="off")

    await _dispatcher(sm)(_event(INTAKE_EVENT, workspace_id=ids["workspace"]))

    assert len(await _inbox_rows(sm, account_a)) == 1
    logs_a = await _log_rows(sm, account_a)
    assert len(logs_a) == 1
    assert logs_a[0].action_taken == "notification_created"

    assert await _inbox_rows(sm, account_b) == []
    logs_b = await _log_rows(sm, account_b)
    assert len(logs_b) == 1
    assert logs_b[0].action_taken == "suppressed_by_preference"


# --- Scenario 6: the full frozen catalog, category + severity per event ---


def test_catalog_covers_exactly_the_frozen_section_2_events() -> None:
    """The dispatcher's CATALOG is the frozen table — nothing missing, nothing
    invented — and every (category, severity) pair matches the document."""
    from oryx.services.activity.dispatcher import CATALOG, SUBSCRIBED_EVENTS

    assert set(CATALOG) == set(FROZEN_SECTION_2)
    assert set(SUBSCRIBED_EVENTS) == set(FROZEN_SECTION_2)
    for name, (category, severity) in FROZEN_SECTION_2.items():
        assert (CATALOG[name].category, CATALOG[name].severity) == (category, severity), name


@pytest.mark.asyncio
@pytest.mark.parametrize(("event_name", "expected"), sorted(FROZEN_SECTION_2.items()))
async def test_frozen_catalog_event_maps_to_category_and_severity(
    sm, event_name: str, expected: tuple[str, str]
) -> None:
    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]

    await _dispatcher(sm)(_event(event_name, workspace_id=ids["workspace"]))

    inbox = await _inbox_rows(sm, account)
    assert len(inbox) == 1
    category, severity = expected
    assert inbox[0].type == category
    assert inbox[0].severity == severity
    assert inbox[0].source_event_type == event_name


# --- Scenario 7: the Wave C push boundary is not crossed ---


@pytest.mark.asyncio
async def test_push_channel_boundary_not_crossed(sm) -> None:
    """Channel independence (updated for Wave C, which made this two-sided):
    a push-channel 'off' preference must NOT suppress the in_app notification,
    the dispatcher must not write preference rows, and — now that the push
    step exists — an explicit push-off means NO push attempt and NO push
    decision row at all (the in_app suppression vocabulary never bleeds into
    the push slot)."""
    from oryx.core.models import AlertPreference

    ids = await _seed_workspace(sm)
    account = ids["accounts"][0]
    await _set_preference(
        sm, account_id=account, type_="system", channel="push", frequency="off"
    )

    await _dispatcher(sm)(_event(INTAKE_EVENT, workspace_id=ids["workspace"]))

    # in_app dispatch went ahead: the push-channel row didn't suppress it.
    assert len(await _inbox_rows(sm, account)) == 1
    logs = await _log_rows(sm, account)
    assert [log.action_taken for log in logs] == ["notification_created"]
    # Push disabled → the push slot stays empty (no push_sent/push_failed).
    assert await _log_rows(sm, account, channel="push") == []

    # The dispatcher reads preferences; it never writes them.
    async with sm() as session:
        prefs = (
            (
                await session.execute(
                    select(AlertPreference).where(AlertPreference.account_id == account)
                )
            )
            .scalars()
            .all()
        )
    assert [(p.channel, p.frequency) for p in prefs] == [("push", "off")]


# --- Scenario 8: one explicit test per severity level ---


@pytest.mark.asyncio
async def test_severity_info_for_intake_item_received(sm) -> None:
    ids = await _seed_workspace(sm)
    await _dispatcher(sm)(_event("intake.item.received", workspace_id=ids["workspace"]))
    inbox = await _inbox_rows(sm, ids["accounts"][0])
    assert len(inbox) == 1
    assert inbox[0].severity == "info"


@pytest.mark.asyncio
async def test_severity_warning_for_conflict_detected(sm) -> None:
    ids = await _seed_workspace(sm)
    await _dispatcher(sm)(
        _event("verification.conflict.detected", workspace_id=ids["workspace"])
    )
    inbox = await _inbox_rows(sm, ids["accounts"][0])
    assert len(inbox) == 1
    assert inbox[0].severity == "warning"


@pytest.mark.asyncio
async def test_severity_error_for_publish_failed(sm) -> None:
    ids = await _seed_workspace(sm)
    await _dispatcher(sm)(_event("content.publish.failed", workspace_id=ids["workspace"]))
    inbox = await _inbox_rows(sm, ids["accounts"][0])
    assert len(inbox) == 1
    assert inbox[0].severity == "error"
