"""RssProvider sync loop.

The provider class is the unit the orchestrator depends on. Construction
is cheap; one provider instance per request is fine.

Cursor shape:
  {"etag": "...", "last_modified": "...", "feed_url": "..."}

The orchestrator stores it as opaque jsonb in `intake_sources.cursor`.

CR-10 redirect handling lives here, not in the client — the client just
reports a `REDIRECT_PERMANENT` outcome. We pass the new URL back to the
caller (via the SyncResult) so the orchestrator can persist it on the
originating Phase 2 row.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from oryx.services.intake.providers.base import (
    IntakeSourceKind,
    RawItem,
    SyncCursor,
    ValidationResult,
    ValidationStatus,
)
from oryx.services.intake.providers.rss.client import (
    FetchOutcome,
    fetch_feed,
)
from oryx.services.intake.providers.rss.config_schema import RssSourceConfig
from oryx.services.intake.providers.rss.mapper import parsed_item_to_raw
from oryx.services.intake.providers.rss.parser import parse_feed


@dataclass(frozen=True)
class RssSyncReport:
    """Surface what happened so the orchestrator can audit + persist."""

    new_etag: str | None
    new_last_modified: str | None
    items_yielded: int
    permanent_redirect_to: str | None  # CR-10 — caller persists this


class RssProvider:
    """Stateless. One instance per sync request is the simplest pattern."""

    name = "rss"
    kind = IntakeSourceKind.RSS

    def __init__(self) -> None:
        # Per-instance report so the caller can introspect after the
        # async-for completes. Cleaner than mutable cursor objects.
        self._last_report: RssSyncReport | None = None

    @property
    def last_report(self) -> RssSyncReport | None:
        return self._last_report

    async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        try:
            RssSourceConfig.model_validate(config)
            return ValidationResult(status=ValidationStatus.OK)
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.INVALID, message=str(e)
            )

    async def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        parsed_config = RssSourceConfig.model_validate(config)
        c = cursor.value if cursor else {}

        result = await fetch_feed(
            str(parsed_config.feed_url),
            etag=c.get("etag"),
            last_modified=c.get("last_modified"),
            user_agent=parsed_config.user_agent,
        )

        # 304 — nothing new
        if result.outcome == FetchOutcome.NOT_MODIFIED:
            self._last_report = RssSyncReport(
                new_etag=result.etag or c.get("etag"),
                new_last_modified=result.last_modified or c.get("last_modified"),
                items_yielded=0,
                permanent_redirect_to=None,
            )
            return

        # 301 — persist new URL upstream and stop. The caller initiates a
        # follow-up sync with the new URL on the next tick.
        if result.outcome == FetchOutcome.REDIRECT_PERMANENT:
            self._last_report = RssSyncReport(
                new_etag=None,
                new_last_modified=None,
                items_yielded=0,
                permanent_redirect_to=result.final_url,
            )
            return

        # OK — parse and yield. Body is guaranteed non-None here.
        assert result.body is not None
        feed = parse_feed(result.body, fallback_feed_url=str(parsed_config.feed_url))
        count = 0
        for item in feed.items:
            count += 1
            yield parsed_item_to_raw(item, feed_title=feed.feed_title)

        self._last_report = RssSyncReport(
            new_etag=result.etag,
            new_last_modified=result.last_modified,
            items_yielded=count,
            permanent_redirect_to=None,
        )


def cursor_from_report(report: RssSyncReport) -> dict[str, Any]:
    """Build the new cursor dict the orchestrator should persist."""
    out: dict[str, Any] = {}
    if report.new_etag:
        out["etag"] = report.new_etag
    if report.new_last_modified:
        out["last_modified"] = report.new_last_modified
    return out
