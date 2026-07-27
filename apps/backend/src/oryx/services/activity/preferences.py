"""Notification-preference default resolution — the SINGLE source of truth.

The frozen architecture (docs/PHASE_6_ARCHITECTURE.md §3.2) keeps the
alert_preferences table small: a row only exists once someone changes a default.
A *missing* (account, category, channel) row therefore means "default enabled".

Two pieces of code must agree on what that default is:
  - the NotificationDispatcher (services/activity/dispatcher.py), deciding
    whether to create or suppress a notification;
  - GET /v1/activity/alerts/preferences (services/activity/router.py),
    resolving defaults server-side so the client never reconstructs them.

Both import from here, so the agreement is structural — and Wave A asserts it
directly with a test. Phase 6 only ever resolves the four real content
categories; the reserved cadence-label activity_type values
(instant_alert/daily_digest/weekly_digest) are never used on alert_preferences.

Team Chat foundation wave adds a fifth category, 'chat' — a single global
toggle across in_app/push/email (per-conversation granularity is out of
scope while there is only one workspace-wide channel to have granularity
over). It resolves through the exact same default logic below; no new
endpoint or preference concept was built for it.
"""
from __future__ import annotations

# A missing alert_preferences row resolves to this frequency ("enabled").
DEFAULT_ALERT_FREQUENCY = "instant"

# The real content categories Phase 6 (+ the Team Chat foundation wave)
# reads/writes on alert_preferences.
NOTIFICATION_CATEGORIES: tuple[str, ...] = (
    "security",
    "system",
    "verification",
    "publishing",
    "chat",
)

# The delivery channels the preference grid resolves defaults for. Phase 6
# Wave A only *dispatches* on in_app; push/email delivery is Wave C, but the
# resolved grid exposes them so the client gets a complete view from day one.
RESOLVED_CHANNELS: tuple[str, ...] = ("in_app", "push", "email")


def resolve_frequency(existing: str | None) -> str:
    """An existing row wins; a missing row falls back to the default."""
    return existing if existing is not None else DEFAULT_ALERT_FREQUENCY


def is_enabled(frequency: str) -> bool:
    """Any frequency other than 'off' means a notification should be delivered."""
    return frequency != "off"
