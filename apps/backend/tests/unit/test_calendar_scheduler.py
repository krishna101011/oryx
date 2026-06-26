"""Calendar scheduler policy — grace-window + backoff math.

DB-free pure-function tests (the fire/re-drive passes are exercised by the
requires_db integration suite). Mirrors the intake scheduler's source_is_due
unit-test style.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from oryx.services.calendar.scheduler import (
    GRACE_WINDOW,
    RETRY_BACKOFF,
    retry_due,
    within_grace,
)

NOW = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# within_grace — 15-minute window
# ---------------------------------------------------------------------------

def test_grace_window_is_fifteen_minutes() -> None:
    assert GRACE_WINDOW == timedelta(minutes=15)


def test_entry_exactly_due_is_within_grace() -> None:
    assert within_grace(scheduled_at=NOW, now=NOW)


def test_entry_fourteen_minutes_late_is_within_grace() -> None:
    assert within_grace(scheduled_at=NOW - timedelta(minutes=14), now=NOW)


def test_entry_sixteen_minutes_late_is_beyond_grace() -> None:
    assert not within_grace(scheduled_at=NOW - timedelta(minutes=16), now=NOW)


def test_grace_boundary_is_exclusive_at_fifteen_minutes() -> None:
    # exactly 15 min late: now - 15min == scheduled_at, not strictly greater.
    assert not within_grace(scheduled_at=NOW - timedelta(minutes=15), now=NOW)


# ---------------------------------------------------------------------------
# retry_due — exponential backoff (5 min / 30 min / 2 hr)
# ---------------------------------------------------------------------------

def test_backoff_intervals_match_frozen_schedule() -> None:
    assert RETRY_BACKOFF[1] == timedelta(minutes=5)
    assert RETRY_BACKOFF[2] == timedelta(minutes=30)
    assert RETRY_BACKOFF[3] == timedelta(hours=2)


def test_tier1_not_due_before_five_minutes() -> None:
    assert not retry_due(
        attempt_count=1, last_attempt_at=NOW - timedelta(minutes=4), now=NOW
    )


def test_tier1_due_after_five_minutes() -> None:
    assert retry_due(
        attempt_count=1, last_attempt_at=NOW - timedelta(minutes=5), now=NOW
    )


def test_tier2_not_due_before_thirty_minutes() -> None:
    # 6 minutes would have been enough for tier 1, but tier 2 waits 30.
    assert not retry_due(
        attempt_count=2, last_attempt_at=NOW - timedelta(minutes=6), now=NOW
    )


def test_tier2_due_after_thirty_minutes() -> None:
    assert retry_due(
        attempt_count=2, last_attempt_at=NOW - timedelta(minutes=31), now=NOW
    )


def test_tier3_due_after_two_hours_only() -> None:
    assert not retry_due(
        attempt_count=3, last_attempt_at=NOW - timedelta(hours=1), now=NOW
    )
    assert retry_due(
        attempt_count=3, last_attempt_at=NOW - timedelta(hours=2), now=NOW
    )


def test_attempt_count_zero_is_never_a_retry_candidate() -> None:
    # attempt_count 0 = never attempted; not a transient-retry row.
    assert not retry_due(attempt_count=0, last_attempt_at=None, now=NOW)


def test_attempt_count_five_is_terminal_not_retried() -> None:
    # Wave D marks attempt 5 'failed'; the re-drive must never touch it.
    assert not retry_due(
        attempt_count=5, last_attempt_at=NOW - timedelta(days=1), now=NOW
    )


def test_pending_row_without_recorded_time_is_due() -> None:
    # Defensive: a pending row with attempts but no last_attempt_at is not
    # stranded.
    assert retry_due(attempt_count=2, last_attempt_at=None, now=NOW)
