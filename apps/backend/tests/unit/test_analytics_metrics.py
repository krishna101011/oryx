"""ACTION_METRICS drift guard — the email-family regression (2026-07-21).

The rollup worker silently skips any automation_log.action_taken value not in
ACTION_METRICS (rollup.py's `if row.action_taken in ACTION_METRICS`), so a
dispatcher action added after the map froze vanishes from analytics with no
error anywhere. That happened once for real: ACTION_EMAIL_* shipped with the
Phase 6 email channel and 2,018 real email_sent rows accumulated with zero
rollup representation. These tests make the map's coverage of the dispatcher's
REAL vocabulary a hard invariant instead of a comment — the same shape as
aggregator.py's import-time ANALYTICS_EVENTS == EVENT_METRICS assert, but for
Source B.
"""
from __future__ import annotations

from oryx.services.activity import dispatcher
from oryx.services.analytics.metrics import ACTION_METRICS, EVENT_METRICS
from oryx.services.verification.events.constants import AI_PARSE_FAILED


def _dispatcher_action_values() -> set[str]:
    """Every module-level ACTION_* string constant dispatcher.py defines —
    reflected, not hand-listed, so a new constant is picked up automatically."""
    return {
        value
        for name, value in vars(dispatcher).items()
        if name.startswith("ACTION_") and isinstance(value, str)
    }


def test_action_metrics_covers_every_dispatcher_action_constant() -> None:
    actions = _dispatcher_action_values()
    # Reflection sanity: the known-real vocabulary must be present, otherwise
    # an import refactor could silently reduce this test to comparing two
    # empty sets.
    assert {"notification_created", "push_failed", "email_sent"} <= actions

    missing = actions - set(ACTION_METRICS)
    assert not missing, (
        f"dispatcher actions with NO metric mapping (rollup silently drops "
        f"their automation_log rows): {sorted(missing)}"
    )
    unknown = set(ACTION_METRICS) - actions
    assert not unknown, (
        f"ACTION_METRICS keys matching no real dispatcher constant (dead or "
        f"typo'd mappings that can never aggregate anything): {sorted(unknown)}"
    )


def test_action_metric_keys_are_unique() -> None:
    # Two actions sharing one metric key would silently merge their counts
    # into a single rollup series.
    values = list(ACTION_METRICS.values())
    assert len(values) == len(set(values))


# --- verification.ai.parse_failed (post-freeze §3.3 extension, 2026-07-22) ---


def test_parse_failed_event_maps_to_its_metric() -> None:
    assert EVENT_METRICS[AI_PARSE_FAILED] == "ai_parse_failures_total"
    # Same silent-drop guard as Source B: an unmapped event's facts vanish
    # from rollups with no error anywhere.
    values = list(EVENT_METRICS.values())
    assert len(values) == len(set(values))


def test_parse_failed_event_never_routes_to_the_dispatcher() -> None:
    """MANDATORY constraint of the 2026-07-22 ADR: the parse-failure event is
    observational only. Verified against the dispatcher's REAL catalog and
    subscription tuple — not assumed."""
    assert AI_PARSE_FAILED not in dispatcher.CATALOG
    assert AI_PARSE_FAILED not in dispatcher.SUBSCRIBED_EVENTS
