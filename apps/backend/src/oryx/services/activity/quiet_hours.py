"""Quiet-hours evaluation — Phase 6 Wave C.

alert_preferences.quiet_hours has been stored and API-writable since Phase 2
({"start": "HH:MM", "end": "HH:MM", "tz": "IANA name"}, the shared-types
QuietHours mirror) but nothing ever evaluated it. This is that evaluator.

Semantics:
  - The window is compared in the ACCOUNT'S OWN timezone — the tz the client
    captured into the value itself — never server-local or hardcoded UTC,
    matching the DigestWorker's local-time resolution principle. An unknown tz
    falls back to UTC with a warning (same tolerance as digest._safe_zone).
  - The window is half-open [start, end): a push at exactly `start` is quiet,
    one at exactly `end` is not.
  - Overnight windows wrap midnight: start > end (e.g. 22:00-07:00) means
    quiet when now >= start OR now < end. No start < end assumption anywhere.
  - start == end is an EMPTY window (never quiet). This is the documented
    "off" encoding: UpdateAlertPreferenceRequest cannot null out quiet_hours
    once set (the PUT only writes the field when a value is present), so the
    client clears the window by writing 00:00-00:00.
  - Malformed values fail OPEN (deliver, with a warning log): a corrupt
    preference must degrade to normal delivery, not silently mute an account.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from oryx.core.logging import get_logger

logger = get_logger(__name__)


def _parse_hhmm(value: Any) -> time | None:
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour=hour, minute=minute)


def is_quiet_now(
    quiet_hours: Mapping[str, Any] | None, *, now: datetime | None = None
) -> bool:
    """True when `now` falls inside the account's quiet window.

    `quiet_hours` is the raw JSONB value off an alert_preferences row (or
    None). `now` must be an aware datetime; it defaults to the real clock and
    is injectable for tests.
    """
    if not quiet_hours:
        return False

    start = _parse_hhmm(quiet_hours.get("start"))
    end = _parse_hhmm(quiet_hours.get("end"))
    if start is None or end is None:
        logger.warning(
            "quiet_hours.malformed",
            extra={"start": quiet_hours.get("start"), "end": quiet_hours.get("end")},
        )
        return False

    if start == end:
        return False  # empty window — the client's "off" encoding

    tz_name = quiet_hours.get("tz")
    try:
        tz = ZoneInfo(tz_name) if isinstance(tz_name, str) else ZoneInfo("UTC")
    except (KeyError, ValueError):
        logger.warning("quiet_hours.bad_timezone", extra={"timezone": tz_name})
        tz = ZoneInfo("UTC")

    moment = now if now is not None else datetime.now(UTC)
    local = moment.astimezone(tz).time().replace(second=0, microsecond=0)

    if start < end:
        return start <= local < end
    # Overnight wrap (e.g. 22:00-07:00): quiet late evening OR early morning.
    return local >= start or local < end
