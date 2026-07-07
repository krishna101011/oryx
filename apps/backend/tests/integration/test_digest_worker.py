"""DigestWorker — Phase 6 Wave B coverage.

Drives DigestWorker.tick(now=...) with injected instants (the same
deterministic-now technique as test_calendar_scheduler.py) against seeded
accounts/preferences/inbox rows, asserting on the SPECIFIC seeded rows' end
state — never global counts (oryx_test accumulates rows across runs; see the
oryx-architect Operational Reality note on global background workers).

The eight mandatory Wave B scenarios each get a named test below:
  1. daily fires after local 08:00           test_daily_digest_fires_after_local_0800
  2. weekly fires only Monday local 08:00    test_weekly_digest_fires_only_at_monday_local_0800
  3. off/instant accounts get no digest      test_no_digest_for_off_or_instant_frequency
  4. double tick in one window is a no-op    test_double_tick_same_window_is_idempotent
  5. two timezones fire at own local time    test_two_timezones_fire_at_their_own_local_times
  6. zero activity → nothing written         test_zero_activity_window_writes_nothing
  7. bundling: all rows, none lost/duped     test_bundling_references_every_row_exactly_once
  8. DST boundary send time                  test_dst_boundary_uses_post_transition_offset
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db

DIGEST_TYPES = ("daily_digest", "weekly_digest")


async def _seed_account(sm, *, timezone: str, created_at: datetime, frequency: str,
                        category: str = "system", channel: str = "in_app") -> uuid.UUID:
    """Account + profile(timezone) + one alert_preferences row."""
    from oryx.core.models import Account, AlertPreference, Profile

    account_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            Account(
                id=account_id,
                email=f"digest+{account_id.hex[:8]}@oryx.test",
                password_hash="x",
                password_changed_at=created_at,
                created_at=created_at,
                status="active",
            )
        )
        await session.flush()
        session.add(
            Profile(account_id=account_id, display_name="Digest", timezone=timezone)
        )
        session.add(
            AlertPreference(
                account_id=account_id, type=category, channel=channel,
                frequency=frequency,
            )
        )
        await session.commit()
    return account_id


async def _seed_inbox_row(sm, *, account_id: uuid.UUID, created_at: datetime,
                          category: str = "system", title: str = "Seeded item",
                          severity: str = "info") -> uuid.UUID:
    from oryx.core.models import ActivityInbox

    row_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            ActivityInbox(
                id=row_id, account_id=account_id, workspace_id=None,
                type=category, severity=severity, title=title, body=None,
                data={}, created_at=created_at,
            )
        )
        await session.commit()
    return row_id


async def _digest_rows(sm, account_id: uuid.UUID):
    from oryx.core.models import ActivityInbox

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(ActivityInbox).where(
                        ActivityInbox.account_id == account_id,
                        ActivityInbox.type.in_(DIGEST_TYPES),
                    ).order_by(ActivityInbox.created_at)
                )
            )
            .scalars()
            .all()
        )


async def _run_rows(sm, account_id: uuid.UUID):
    from oryx.core.models import DigestRun

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(DigestRun).where(DigestRun.account_id == account_id)
                    .order_by(DigestRun.window_end)
                )
            )
            .scalars()
            .all()
        )


def _worker(sm):
    from oryx.services.activity.digest import DigestWorker

    return DigestWorker(sm)


# --- Scenario 1: daily fires once local time crosses 08:00 ---


@pytest.mark.asyncio
async def test_daily_digest_fires_after_local_0800(sm) -> None:
    """Asia/Kolkata (UTC+5:30) daily account with one row in the window:
    at 07:30 local nothing fires; at 08:30 local the digest lands."""
    account = await _seed_account(
        sm, timezone="Asia/Kolkata", frequency="daily",
        created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    worker = _worker(sm)

    # 2026-07-06 02:00 UTC == 07:30 IST — before the local send point.
    await worker.tick(now=datetime(2026, 7, 6, 2, 0, tzinfo=UTC))
    assert await _digest_rows(sm, account) == []

    # 2026-07-06 03:00 UTC == 08:30 IST — past local 08:00.
    await worker.tick(now=datetime(2026, 7, 6, 3, 0, tzinfo=UTC))
    digests = await _digest_rows(sm, account)
    assert len(digests) == 1
    assert digests[0].type == "daily_digest"
    assert digests[0].data["count"] == 1
    runs = await _run_rows(sm, account)
    assert len(runs) == 1
    assert runs[0].frequency == "daily"
    assert runs[0].activity_type == "system"
    # window_end is the local 08:00 send point expressed in UTC (02:30 UTC).
    assert runs[0].window_end == datetime(2026, 7, 6, 2, 30, tzinfo=UTC)


# --- Scenario 2: weekly fires only at Monday local 08:00 ---


@pytest.mark.asyncio
async def test_weekly_digest_fires_only_at_monday_local_0800(sm) -> None:
    """UTC weekly account: Sunday tick and Monday-07:00 tick write nothing;
    Monday 08:30 fires; Tuesday tick does not fire a second one."""
    account = await _seed_account(
        sm, timezone="UTC", frequency="weekly",
        created_at=datetime(2026, 6, 30, 10, 0, tzinfo=UTC),  # a Tuesday
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    )
    worker = _worker(sm)

    # Sunday 2026-07-05 09:00 UTC — not Monday, nothing due yet.
    await worker.tick(now=datetime(2026, 7, 5, 9, 0, tzinfo=UTC))
    assert await _digest_rows(sm, account) == []

    # Monday 2026-07-06 07:00 UTC — Monday, but before local 08:00.
    await worker.tick(now=datetime(2026, 7, 6, 7, 0, tzinfo=UTC))
    assert await _digest_rows(sm, account) == []

    # Monday 2026-07-06 08:30 UTC — the weekly send point has passed.
    await worker.tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))
    digests = await _digest_rows(sm, account)
    assert len(digests) == 1
    assert digests[0].type == "weekly_digest"

    # Tuesday 2026-07-07 09:00 UTC — same window, no second digest.
    await worker.tick(now=datetime(2026, 7, 7, 9, 0, tzinfo=UTC))
    assert len(await _digest_rows(sm, account)) == 1
    assert len(await _run_rows(sm, account)) == 1


# --- Scenario 3: 'off' and 'instant' frequencies never digest ---


@pytest.mark.asyncio
async def test_no_digest_for_off_or_instant_frequency(sm) -> None:
    created = datetime(2026, 7, 3, 0, 0, tzinfo=UTC)
    off_account = await _seed_account(
        sm, timezone="UTC", frequency="off", created_at=created
    )
    instant_account = await _seed_account(
        sm, timezone="UTC", frequency="instant", created_at=created
    )
    for account in (off_account, instant_account):
        await _seed_inbox_row(
            sm, account_id=account, created_at=datetime(2026, 7, 4, 12, 0, tzinfo=UTC)
        )

    await _worker(sm).tick(now=datetime(2026, 7, 6, 9, 0, tzinfo=UTC))

    for account in (off_account, instant_account):
        assert await _digest_rows(sm, account) == []
        assert await _run_rows(sm, account) == []


# --- Scenario 4: idempotency inside one window ---


@pytest.mark.asyncio
async def test_double_tick_same_window_is_idempotent(sm) -> None:
    """Two ticks inside the same daily window: exactly ONE digest_runs row and
    ONE digest inbox row — the second tick short-circuits on the unique key."""
    account = await _seed_account(
        sm, timezone="UTC", frequency="daily",
        created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    worker = _worker(sm)

    await worker.tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))
    await worker.tick(now=datetime(2026, 7, 6, 8, 31, tzinfo=UTC))

    assert len(await _digest_rows(sm, account)) == 1
    assert len(await _run_rows(sm, account)) == 1


# --- Scenario 5: the whole point of the wave — per-account local send times ---


@pytest.mark.asyncio
async def test_two_timezones_fire_at_their_own_local_times(sm) -> None:
    """Kolkata (UTC+5:30) and New York (UTC-4 in July) daily accounts, rows in
    both feeds. At 03:00 UTC only Kolkata's 08:00 has passed; New York's fires
    at its OWN send point (12:00 UTC), a different UTC instant."""
    kolkata = await _seed_account(
        sm, timezone="Asia/Kolkata", frequency="daily",
        created_at=datetime(2026, 7, 5, 5, 0, tzinfo=UTC),
    )
    new_york = await _seed_account(
        sm, timezone="America/New_York", frequency="daily",
        created_at=datetime(2026, 7, 5, 14, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=kolkata, created_at=datetime(2026, 7, 5, 6, 0, tzinfo=UTC)
    )
    await _seed_inbox_row(
        sm, account_id=new_york, created_at=datetime(2026, 7, 5, 15, 0, tzinfo=UTC)
    )
    worker = _worker(sm)

    # 2026-07-06 03:00 UTC == 08:30 IST (past Kolkata's send point) but
    # 23:00 2026-07-05 EDT (New York's next 08:00 hasn't arrived).
    await worker.tick(now=datetime(2026, 7, 6, 3, 0, tzinfo=UTC))
    assert len(await _digest_rows(sm, kolkata)) == 1
    assert await _digest_rows(sm, new_york) == []

    # 2026-07-06 12:30 UTC == 08:30 EDT — New York's own local send point.
    await worker.tick(now=datetime(2026, 7, 6, 12, 30, tzinfo=UTC))
    ny_runs = await _run_rows(sm, new_york)
    assert len(ny_runs) == 1
    # New York's window closed at ITS local 08:00 == 12:00 UTC, not Kolkata's.
    assert ny_runs[0].window_end == datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    kolkata_runs = await _run_rows(sm, kolkata)
    assert len(kolkata_runs) == 1
    assert kolkata_runs[0].window_end == datetime(2026, 7, 6, 2, 30, tzinfo=UTC)


# --- Scenario 6: silence, not an empty digest ---


@pytest.mark.asyncio
async def test_zero_activity_window_writes_nothing(sm) -> None:
    """A daily account with NO feed rows in the window: no digest inbox row
    AND no digest_runs row — the empty window folds into the next one."""
    account = await _seed_account(
        sm, timezone="UTC", frequency="daily",
        created_at=datetime(2026, 7, 4, 0, 0, tzinfo=UTC),
    )

    await _worker(sm).tick(now=datetime(2026, 7, 6, 9, 0, tzinfo=UTC))

    assert await _digest_rows(sm, account) == []
    assert await _run_rows(sm, account) == []


# --- Scenario 7: bundling covers every row exactly once ---


@pytest.mark.asyncio
async def test_bundling_references_every_row_exactly_once(sm) -> None:
    """Three rows in window 1 → one digest referencing exactly those three;
    two more rows before window 2 → a second digest referencing exactly the
    two new ids. Disjoint sets: nothing lost, nothing double-bundled."""
    account = await _seed_account(
        sm, timezone="UTC", frequency="daily",
        created_at=datetime(2026, 7, 4, 0, 0, tzinfo=UTC),
    )
    first_batch = {
        str(
            await _seed_inbox_row(
                sm, account_id=account, title=f"first-{i}",
                created_at=datetime(2026, 7, 5, 10 + i, 0, tzinfo=UTC),
            )
        )
        for i in range(3)
    }
    worker = _worker(sm)
    await worker.tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    second_batch = {
        str(
            await _seed_inbox_row(
                sm, account_id=account, title=f"second-{i}",
                created_at=datetime(2026, 7, 6, 10 + i, 0, tzinfo=UTC),
            )
        )
        for i in range(2)
    }
    await worker.tick(now=datetime(2026, 7, 7, 8, 30, tzinfo=UTC))

    digests = await _digest_rows(sm, account)
    assert len(digests) == 2
    assert set(digests[0].data["bundled_ids"]) == first_batch
    assert digests[0].data["count"] == 3
    assert set(digests[1].data["bundled_ids"]) == second_batch
    assert digests[1].data["count"] == 2
    # A digest never bundles another digest.
    all_bundled = set(digests[0].data["bundled_ids"]) | set(digests[1].data["bundled_ids"])
    assert str(digests[0].id) not in all_bundled


# --- Scenario 8: DST boundary — local 08:00 tracks the new offset ---


@pytest.mark.asyncio
async def test_dst_boundary_uses_post_transition_offset(sm) -> None:
    """America/New_York the day after 2026's spring-forward (2026-03-08):
    local 08:00 is now 12:00 UTC (EDT), not 13:00 UTC (EST). A tick at
    12:30 UTC must fire; a tick at 11:30 UTC (07:30 local) must not."""
    account = await _seed_account(
        sm, timezone="America/New_York", frequency="daily",
        created_at=datetime(2026, 3, 8, 13, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC)
    )
    worker = _worker(sm)

    # 2026-03-09 11:30 UTC == 07:30 EDT — before local 08:00.
    await worker.tick(now=datetime(2026, 3, 9, 11, 30, tzinfo=UTC))
    assert await _digest_rows(sm, account) == []

    # 2026-03-09 12:30 UTC == 08:30 EDT. Under the stale EST offset the send
    # point would wrongly be 13:00 UTC and this tick would do nothing.
    await worker.tick(now=datetime(2026, 3, 9, 12, 30, tzinfo=UTC))
    runs = await _run_rows(sm, account)
    assert len(runs) == 1
    assert runs[0].window_end == datetime(2026, 3, 9, 12, 0, tzinfo=UTC)
    assert len(await _digest_rows(sm, account)) == 1
