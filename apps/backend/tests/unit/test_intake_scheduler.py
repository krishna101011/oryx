"""Scheduler due-time policy + provider factory dispatch.

DB-free: pick_due/tick are exercised by the requires_db integration suite.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from anant.services.intake.providers.api_pull.sync import (
    ApiPullProvider,
    ApiPullSyncReport,
)
from anant.services.intake.providers.gmail.sync import GmailProvider, GmailSyncReport
from anant.services.intake.providers.rss.sync import RssProvider, RssSyncReport
from anant.services.intake.scheduler import (
    PROBE_INTERVAL,
    failure_backoff,
    fetch_interval,
    source_is_due,
)
from anant.services.intake.sync_runner import (
    SourceSnapshot,
    _cursor_from_report,
    build_provider,
)

NOW = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)


def _due(**overrides: object) -> bool:
    kwargs: dict = dict(
        kind="rss",
        status="healthy",
        enabled=True,
        config={},
        last_attempt_at=None,
        consecutive_failures=0,
        now=NOW,
    )
    kwargs.update(overrides)
    return source_is_due(**kwargs)


def _snapshot(kind: str, config: dict | None = None) -> SourceSnapshot:
    return SourceSnapshot(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        kind=kind,
        config=config or {},
        cursor=None,
        status="healthy",
        consecutive_failures=0,
        origin_custom_id=None,
    )


# ---------------------------------------------------------------------------
# source_is_due
# ---------------------------------------------------------------------------

def test_never_attempted_source_is_due() -> None:
    assert _due(last_attempt_at=None)


def test_manual_sync_reset_makes_source_due() -> None:
    # The router clears last_attempt_at on POST /sources/:id/sync.
    assert _due(last_attempt_at=None, consecutive_failures=3)


def test_healthy_source_waits_for_fetch_interval() -> None:
    assert not _due(last_attempt_at=NOW - timedelta(minutes=10))   # rss default 30
    assert _due(last_attempt_at=NOW - timedelta(minutes=31))


def test_fetch_interval_honors_config_override() -> None:
    cfg = {"fetch_interval_minutes": 5}
    assert _due(config=cfg, last_attempt_at=NOW - timedelta(minutes=6))
    assert not _due(config=cfg, last_attempt_at=NOW - timedelta(minutes=4))


def test_failing_source_follows_backoff_curve_not_interval() -> None:
    # 3 failures → 240s backoff: due well before the 30-min RSS interval.
    assert _due(
        consecutive_failures=3,
        last_attempt_at=NOW - failure_backoff(3),
    )
    assert not _due(
        consecutive_failures=3,
        last_attempt_at=NOW - failure_backoff(3) + timedelta(seconds=5),
    )


def test_degraded_source_probes_hourly_only() -> None:
    assert not _due(status="degraded", last_attempt_at=NOW - timedelta(minutes=59))
    assert _due(status="degraded", last_attempt_at=NOW - PROBE_INTERVAL)


def test_auth_required_and_disabled_never_due() -> None:
    assert not _due(status="auth_required", last_attempt_at=NOW - timedelta(days=9))
    assert not _due(status="disabled", last_attempt_at=None)


def test_disabled_flag_and_non_pollable_kinds_never_due() -> None:
    assert not _due(enabled=False)
    assert not _due(kind="webhook")
    assert not _due(kind="manual")


def test_failure_backoff_is_capped_at_one_hour() -> None:
    assert failure_backoff(0).total_seconds() == 30
    assert failure_backoff(20).total_seconds() == 3600


def test_per_kind_default_intervals() -> None:
    assert fetch_interval("rss", {}) == timedelta(minutes=30)
    assert fetch_interval("gmail", {}) == timedelta(minutes=15)
    assert fetch_interval("api_pull", {}) == timedelta(minutes=15)


# ---------------------------------------------------------------------------
# Provider factory + cursor dispatch
# ---------------------------------------------------------------------------

def test_factory_builds_the_right_provider_per_kind() -> None:
    sm = object()  # never touched at construction time
    assert isinstance(build_provider(_snapshot("rss"), sm), RssProvider)
    assert isinstance(build_provider(_snapshot("gmail"), sm), GmailProvider)
    assert isinstance(build_provider(_snapshot("api_pull"), sm), ApiPullProvider)


def test_factory_rejects_push_only_kinds() -> None:
    with pytest.raises(ValueError):
        build_provider(_snapshot("webhook"), object())
    with pytest.raises(ValueError):
        build_provider(_snapshot("manual"), object())


def test_cursor_dispatch_per_provider_report() -> None:
    rss = RssSyncReport(
        new_etag="e1", new_last_modified="lm", items_yielded=2,
        permanent_redirect_to=None,
    )
    assert _cursor_from_report("rss", rss) == {"etag": "e1", "last_modified": "lm"}

    gmail = GmailSyncReport(
        new_history_id="h9", bootstrap_complete=True,
        items_yielded=1, fallback_recovered=False,
    )
    assert _cursor_from_report("gmail", gmail) == {
        "bootstrap_complete": True,
        "history_id": "h9",
    }

    api = ApiPullSyncReport(endpoint_cursors={"/v1/items": "tok"}, items_yielded=3)
    assert _cursor_from_report("api_pull", api) == {
        "endpoints": {"/v1/items": "tok"}
    }
