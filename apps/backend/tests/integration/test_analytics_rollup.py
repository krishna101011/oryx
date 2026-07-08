"""RollupWorker — Phase 7 Wave A coverage (the refresh over both ADR-047 sources).

Isolation note (the standing oryx_test rule): the test DB accumulates rows
across runs and the worker's recompute is a GLOBAL group-by, so every assert
here scopes to this test's own freshly-minted workspace/(metric, date) rows —
never to tick()'s global return value or a global row count.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


async def _seed_workspace(sm) -> dict:
    from oryx.core.models import Account, Workspace, WorkspaceMember

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"rollup+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Rollup WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id, account_id=account.id, role="owner"
            )
        )
        await session.commit()
        return {"workspace": workspace.id, "account": account.id}


async def _seed_raw_event(sm, *, workspace_id, event_name, occurred_at) -> None:
    from oryx.core.models import AnalyticsEventRaw

    async with sm() as session:
        session.add(
            AnalyticsEventRaw(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                source_event_id=uuid.uuid4(),
                event_name=event_name,
                occurred_at=occurred_at,
            )
        )
        await session.commit()


async def _seed_automation_log(
    sm, *, account_id, workspace_id, action_taken, channel, created_at
) -> None:
    from oryx.core.models import AutomationLog

    async with sm() as session:
        session.add(
            AutomationLog(
                id=uuid.uuid4(),
                account_id=account_id,
                workspace_id=workspace_id,
                activity_inbox_id=None,
                triggered_by_event_type="intake.item.received",
                triggered_by_event_id=uuid.uuid4(),
                action_taken=action_taken,
                channel=channel,
                created_at=created_at,
            )
        )
        await session.commit()


async def _seed_digest_run(sm, *, account_id, sent_at) -> None:
    from oryx.core.models import DigestRun

    async with sm() as session:
        session.add(
            DigestRun(
                id=uuid.uuid4(),
                account_id=account_id,
                activity_type="system",
                frequency="daily",
                window_start=sent_at - timedelta(days=1),
                window_end=sent_at,
                sent_at=sent_at,
            )
        )
        await session.commit()


def _worker(sm):
    from oryx.services.analytics.rollup import RollupWorker

    return RollupWorker(sm)


async def _rollups(sm, workspace_id) -> dict[tuple[str, date], int]:
    """This workspace's rollup rows as {(metric_key, date): value}."""
    from oryx.core.models import AnalyticsRollupDaily

    async with sm() as session:
        rows = (
            (
                await session.execute(
                    select(AnalyticsRollupDaily).where(
                        AnalyticsRollupDaily.workspace_id == workspace_id
                    )
                )
            )
            .scalars()
            .all()
        )
    return {(r.metric_key, r.date): r.value for r in rows}


# --- Mandatory scenario 3: Source A raw events -> daily value ---


@pytest.mark.asyncio
async def test_rollup_aggregates_raw_events_into_daily_value(sm) -> None:
    ids = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 9, 0, tzinfo=UTC)
    for _ in range(3):
        await _seed_raw_event(
            sm,
            workspace_id=ids["workspace"],
            event_name="intake.item.received",
            occurred_at=when,
        )
    await _seed_raw_event(
        sm,
        workspace_id=ids["workspace"],
        event_name="content.published",
        occurred_at=when,
    )

    await _worker(sm).tick()

    rollups = await _rollups(sm, ids["workspace"])
    assert rollups[("intake_items_received", date(2026, 7, 8))] == 3
    assert rollups[("drafts_published", date(2026, 7, 8))] == 1


# --- Mandatory scenario 4: Source B tables -> matching metric values ---


@pytest.mark.asyncio
async def test_rollup_aggregates_automation_log_and_digest_runs(sm) -> None:
    ids = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 10, 0, tzinfo=UTC)
    for _ in range(2):
        await _seed_automation_log(
            sm,
            account_id=ids["account"],
            workspace_id=ids["workspace"],
            action_taken="notification_created",
            channel="in_app",
            created_at=when,
        )
    await _seed_automation_log(
        sm,
        account_id=ids["account"],
        workspace_id=ids["workspace"],
        action_taken="push_failed",
        channel="push",
        created_at=when,
    )
    await _seed_digest_run(sm, account_id=ids["account"], sent_at=when)

    await _worker(sm).tick()

    rollups = await _rollups(sm, ids["workspace"])
    day = date(2026, 7, 8)
    assert rollups[("notifications_created", day)] == 2
    assert rollups[("push_failed", day)] == 1
    assert rollups[("digests_sent", day)] == 1


# --- Mandatory scenario 5: double refresh is idempotent, never doubled ---


@pytest.mark.asyncio
async def test_running_the_same_refresh_twice_produces_identical_values(sm) -> None:
    ids = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 11, 0, tzinfo=UTC)
    for _ in range(2):
        await _seed_raw_event(
            sm,
            workspace_id=ids["workspace"],
            event_name="content.draft.created",
            occurred_at=when,
        )
    await _seed_automation_log(
        sm,
        account_id=ids["account"],
        workspace_id=ids["workspace"],
        action_taken="suppressed_by_preference",
        channel="in_app",
        created_at=when,
    )

    worker = _worker(sm)
    await worker.tick()
    first = await _rollups(sm, ids["workspace"])
    await worker.tick()  # same day recomputed — an UPSERT, not an accumulate
    second = await _rollups(sm, ids["workspace"])

    assert first == second
    assert second[("drafts_created", date(2026, 7, 8))] == 2  # not 4
    assert second[("notifications_suppressed_by_preference", date(2026, 7, 8))] == 1


# --- Mandatory scenario 6: workspaces never leak into each other ---


@pytest.mark.asyncio
async def test_two_workspaces_rollups_never_leak(sm) -> None:
    a = await _seed_workspace(sm)
    b = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)
    for _ in range(3):
        await _seed_raw_event(
            sm,
            workspace_id=a["workspace"],
            event_name="intake.item.received",
            occurred_at=when,
        )
    await _seed_raw_event(
        sm,
        workspace_id=b["workspace"],
        event_name="intake.item.received",
        occurred_at=when,
    )

    await _worker(sm).tick()

    day = date(2026, 7, 8)
    assert (await _rollups(sm, a["workspace"]))[("intake_items_received", day)] == 3
    assert (await _rollups(sm, b["workspace"]))[("intake_items_received", day)] == 1


# --- Mandatory scenario 7: quiet-hours metric is zero-safe pre-addendum ---


@pytest.mark.asyncio
async def test_push_suppressed_quiet_hours_reads_as_absent_not_a_crash(sm) -> None:
    """The sparse-zero case: a workspace with push activity but no quiet-hour
    skips gets NO push_suppressed_quiet_hours row, and the refresh completes
    normally. (Originally written pre-addendum, when the dispatcher never
    wrote this value at all; the 2026-07-08 §3.3 extension landed it, and the
    with-data case is test_rollup_picks_up_push_suppressed_quiet_hours_rows —
    this test remains as the zero-data half.)"""
    ids = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 13, 0, tzinfo=UTC)
    await _seed_automation_log(
        sm,
        account_id=ids["account"],
        workspace_id=ids["workspace"],
        action_taken="push_sent",
        channel="push",
        created_at=when,
    )

    await _worker(sm).tick()  # must not raise

    rollups = await _rollups(sm, ids["workspace"])
    assert rollups[("push_sent", date(2026, 7, 8))] == 1
    assert not any(m == "push_suppressed_quiet_hours" for m, _ in rollups)


# --- Quiet-hours addendum (2026-07-08): real rows now feed the metric ---


@pytest.mark.asyncio
async def test_rollup_picks_up_push_suppressed_quiet_hours_rows(sm) -> None:
    """Phase 7 Wave A could only prove this metric read as zero (the
    dispatcher didn't write the value yet). With the §3.3 extension landed,
    a real push_suppressed_quiet_hours decision row must aggregate into the
    metric like any other Source B action."""
    ids = await _seed_workspace(sm)
    when = datetime(2026, 7, 8, 14, 0, tzinfo=UTC)
    for _ in range(2):
        await _seed_automation_log(
            sm,
            account_id=ids["account"],
            workspace_id=ids["workspace"],
            action_taken="push_suppressed_quiet_hours",
            channel="push",
            created_at=when,
        )

    await _worker(sm).tick()

    rollups = await _rollups(sm, ids["workspace"])
    assert rollups[("push_suppressed_quiet_hours", date(2026, 7, 8))] == 2


# --- Mandatory scenario 8: Source B backfills history; Source A cannot ---


@pytest.mark.asyncio
async def test_source_b_backfills_history_but_source_a_never_invents_it(sm) -> None:
    """automation_log/digest_runs carry pre-Wave-A history: the first refresh
    surfaces those days immediately. analytics_events_raw only contains what
    the aggregator recorded since it shipped, so no Source A metric can appear
    for a historical day — the refresh must not invent one."""
    ids = await _seed_workspace(sm)
    past = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)  # long before this wave
    await _seed_automation_log(
        sm,
        account_id=ids["account"],
        workspace_id=ids["workspace"],
        action_taken="notification_created",
        channel="in_app",
        created_at=past,
    )
    await _seed_digest_run(sm, account_id=ids["account"], sent_at=past)

    await _worker(sm).tick()

    rollups = await _rollups(sm, ids["workspace"])
    past_day = date(2026, 6, 1)
    # Source B history is surfaced...
    assert rollups[("notifications_created", past_day)] == 1
    assert rollups[("digests_sent", past_day)] == 1
    # ...and NOT ONE Source A metric exists for that day (nothing was recorded
    # then, so nothing may be invented).
    from oryx.services.analytics.metrics import EVENT_METRICS

    source_a_keys = set(EVENT_METRICS.values())
    assert not any(
        metric in source_a_keys and day == past_day for metric, day in rollups
    )
