"""latest_send_point — pure local-time math, no DB.

Complements tests/integration/test_digest_worker.py: these pin the helper's
wall-clock semantics (daily 08:00 local, weekly Monday 08:00 local, DST
handled by re-localizing dates rather than shifting aware datetimes).
"""
from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from oryx.services.activity.digest import latest_send_point

KOLKATA = ZoneInfo("Asia/Kolkata")
NEW_YORK = ZoneInfo("America/New_York")


def test_daily_before_local_0800_steps_back_a_day() -> None:
    # 02:00 UTC == 07:30 IST → most recent send point is YESTERDAY 08:00 IST.
    got = latest_send_point(
        now=datetime(2026, 7, 6, 2, 0, tzinfo=UTC), tz=KOLKATA, frequency="daily"
    )
    assert got == datetime(2026, 7, 5, 2, 30, tzinfo=UTC)  # 08:00 IST Jul 5


def test_daily_after_local_0800_is_today() -> None:
    got = latest_send_point(
        now=datetime(2026, 7, 6, 3, 0, tzinfo=UTC), tz=KOLKATA, frequency="daily"
    )
    assert got == datetime(2026, 7, 6, 2, 30, tzinfo=UTC)  # 08:00 IST Jul 6


def test_weekly_snaps_to_most_recent_monday() -> None:
    # Sunday 2026-07-05 09:00 UTC → most recent Monday 08:00 is Jun 29.
    got = latest_send_point(
        now=datetime(2026, 7, 5, 9, 0, tzinfo=UTC), tz=ZoneInfo("UTC"),
        frequency="weekly",
    )
    assert got == datetime(2026, 6, 29, 8, 0, tzinfo=UTC)


def test_weekly_monday_before_0800_steps_back_a_week() -> None:
    got = latest_send_point(
        now=datetime(2026, 7, 6, 7, 0, tzinfo=UTC), tz=ZoneInfo("UTC"),
        frequency="weekly",
    )
    assert got == datetime(2026, 6, 29, 8, 0, tzinfo=UTC)


def test_dst_spring_forward_shifts_utc_not_local() -> None:
    # US DST began 2026-03-08. Local 08:00 was 13:00 UTC on Mar 7 (EST) and
    # 12:00 UTC on Mar 9 (EDT) — the LOCAL send hour never moves.
    before = latest_send_point(
        now=datetime(2026, 3, 7, 14, 0, tzinfo=UTC), tz=NEW_YORK, frequency="daily"
    )
    after = latest_send_point(
        now=datetime(2026, 3, 9, 13, 0, tzinfo=UTC), tz=NEW_YORK, frequency="daily"
    )
    assert before == datetime(2026, 3, 7, 13, 0, tzinfo=UTC)
    assert after == datetime(2026, 3, 9, 12, 0, tzinfo=UTC)
    assert before.astimezone(NEW_YORK).hour == after.astimezone(NEW_YORK).hour == 8
