"""Quiet-hours evaluation — Phase 6 Wave C (unit, no DB).

Covers the two MANDATORY Wave C scenarios at the pure-function level (a time
inside the window suppresses; an overnight window evaluates correctly across
midnight) plus the boundary/degradation semantics documented in
services/activity/quiet_hours.py.
"""
from __future__ import annotations

from datetime import UTC, datetime

from oryx.services.activity.quiet_hours import is_quiet_now


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, 7, hour, minute, tzinfo=UTC)


# --- Mandatory scenario 3 (unit half): inside the window suppresses ---


def test_time_inside_same_day_window_is_quiet() -> None:
    qh = {"start": "13:00", "end": "15:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(14, 0)) is True


def test_time_outside_same_day_window_is_not_quiet() -> None:
    qh = {"start": "13:00", "end": "15:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(16, 0)) is False
    assert is_quiet_now(qh, now=_utc(12, 59)) is False


# --- Mandatory scenario 4: overnight window across midnight (22:00-07:00) ---


def test_overnight_window_quiet_before_midnight() -> None:
    qh = {"start": "22:00", "end": "07:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(23, 30)) is True


def test_overnight_window_quiet_after_midnight() -> None:
    qh = {"start": "22:00", "end": "07:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(3, 0)) is True


def test_overnight_window_not_quiet_in_daytime() -> None:
    qh = {"start": "22:00", "end": "07:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(12, 0)) is False
    assert is_quiet_now(qh, now=_utc(21, 59)) is False


def test_window_is_half_open_start_inclusive_end_exclusive() -> None:
    qh = {"start": "22:00", "end": "07:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(22, 0)) is True  # exactly start → quiet
    assert is_quiet_now(qh, now=_utc(7, 0)) is False  # exactly end → not quiet


# --- Timezone resolution: the ACCOUNT's local wall clock decides ---


def test_window_resolves_in_the_accounts_own_timezone() -> None:
    # 22:00-07:00 in Kolkata (UTC+05:30). 18:00 UTC == 23:30 IST → quiet,
    # even though 18:00 UTC is far outside the window read as UTC.
    qh = {"start": "22:00", "end": "07:00", "tz": "Asia/Kolkata"}
    assert is_quiet_now(qh, now=_utc(18, 0)) is True
    # 09:00 UTC == 14:30 IST → daytime in Kolkata → not quiet.
    assert is_quiet_now(qh, now=_utc(9, 0)) is False


def test_unknown_timezone_falls_back_to_utc() -> None:
    qh = {"start": "13:00", "end": "15:00", "tz": "Not/AZone"}
    assert is_quiet_now(qh, now=_utc(14, 0)) is True  # evaluated as UTC


# --- Degradation semantics ---


def test_equal_start_and_end_is_an_empty_window() -> None:
    # The client's documented "off" encoding — never quiet.
    qh = {"start": "00:00", "end": "00:00", "tz": "UTC"}
    assert is_quiet_now(qh, now=_utc(0, 0)) is False
    assert is_quiet_now(qh, now=_utc(12, 0)) is False


def test_missing_value_is_never_quiet() -> None:
    assert is_quiet_now(None, now=_utc(3, 0)) is False
    assert is_quiet_now({}, now=_utc(3, 0)) is False


def test_malformed_values_fail_open() -> None:
    assert is_quiet_now({"start": "25:99", "end": "07:00", "tz": "UTC"}, now=_utc(3)) is False
    assert is_quiet_now({"start": "22:00", "end": "seven", "tz": "UTC"}, now=_utc(3)) is False
    assert is_quiet_now({"start": None, "end": "07:00", "tz": "UTC"}, now=_utc(3)) is False
