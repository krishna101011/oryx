"""Analytics router — Phase 7 Wave B (the dashboard's two read contracts).

GET /v1/analytics/rollups: workspace-scoped daily series read ONLY from
analytics_rollups_daily (docs/PHASE_7_ARCHITECTURE.md §3.2 — every Wave B
chart queries this table, never the raw sources). No aggregation logic here;
Wave A's RollupWorker already computed the values.

GET /v1/analytics/publishing: the §3.4 delivery-performance view — success
rate summed from the same rollups (drafts_published vs publish_failures) plus
time-to-publish, the ONE sanctioned direct query: the draft-creation →
publication gap over recently delivered publications, computed on request and
never persisted. Deliberately NO engagement/view numbers — no real signal
exists (§3.4 demoted that view explicitly rather than faking it).

The /analytics/ping stub route is kept — test_health.py exercises every
service's ping.
"""
from __future__ import annotations

import statistics
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_request_id,
)
from oryx.core.models import AnalyticsRollupDaily, ContentDraft, Publication
from oryx.shared.types import (
    AnalyticsPublishingResponse,
    AnalyticsRollupsResponse,
    PublishingSuccess,
    RollupPoint,
    TimeToPublish,
)

router = APIRouter(tags=["analytics"])

# Default window when the client sends no range: the trailing 30 UTC days.
DEFAULT_RANGE_DAYS = 30
# Time-to-publish sample: the most recent delivered publications. Small and
# bounded — the stats are a dashboard headline, not an export.
TIME_TO_PUBLISH_SAMPLE = 50

PUBLISHED_METRIC = "drafts_published"
FAILED_METRIC = "publish_failures"


@router.get("/analytics/ping")
async def ping(request: Request) -> dict:
    return envelope(
        {"service": "analytics", "pong": True}, request_id=get_request_id(request)
    )


def _resolve_range(from_: date | None, to: date | None) -> tuple[date, date]:
    """Inclusive UTC day bounds; defaults to the trailing DEFAULT_RANGE_DAYS."""
    end = to or datetime.now(UTC).date()
    start = from_ or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        start, end = end, start
    return start, end


@router.get("/analytics/rollups")
async def get_rollups(
    request: Request,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    start, end = _resolve_range(from_, to)
    rows = (
        await db.execute(
            select(
                AnalyticsRollupDaily.metric_key,
                AnalyticsRollupDaily.date,
                AnalyticsRollupDaily.value,
            )
            .where(
                AnalyticsRollupDaily.workspace_id == ws.workspace_id,
                AnalyticsRollupDaily.date >= start,
                AnalyticsRollupDaily.date <= end,
            )
            .order_by(AnalyticsRollupDaily.metric_key, AnalyticsRollupDaily.date)
        )
    ).all()

    series: dict[str, list[RollupPoint]] = {}
    for metric_key, day, value in rows:
        series.setdefault(metric_key, []).append(
            RollupPoint(date=day.isoformat(), value=value)
        )

    payload = AnalyticsRollupsResponse(
        series=series, **{"from": start.isoformat()}, to=end.isoformat()
    )
    return envelope(
        payload.model_dump(by_alias=True), request_id=get_request_id(request)
    )


@router.get("/analytics/publishing")
async def get_publishing(
    request: Request,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    start, end = _resolve_range(from_, to)

    # Success rate: a SUM over the already-correct rollups — not new
    # aggregation, the same read model every chart uses.
    sums = dict(
        (
            await db.execute(
                select(
                    AnalyticsRollupDaily.metric_key,
                    func.sum(AnalyticsRollupDaily.value),
                )
                .where(
                    AnalyticsRollupDaily.workspace_id == ws.workspace_id,
                    AnalyticsRollupDaily.metric_key.in_(
                        [PUBLISHED_METRIC, FAILED_METRIC]
                    ),
                    AnalyticsRollupDaily.date >= start,
                    AnalyticsRollupDaily.date <= end,
                )
                .group_by(AnalyticsRollupDaily.metric_key)
            )
        ).all()
    )
    published = int(sums.get(PUBLISHED_METRIC, 0))
    failed = int(sums.get(FAILED_METRIC, 0))
    attempts = published + failed
    success = PublishingSuccess(
        published=published,
        failed=failed,
        successRate=(published / attempts) if attempts else None,
    )

    # Time-to-publish: the one direct query (§3.4) — recent delivered
    # publications joined to their drafts, gap = published_at - draft
    # creation. Computed here on request, never persisted.
    gaps_rows = (
        await db.execute(
            select(Publication.published_at, ContentDraft.created_at)
            .join(ContentDraft, ContentDraft.id == Publication.draft_id)
            .where(
                Publication.workspace_id == ws.workspace_id,
                Publication.status == "delivered",
                Publication.published_at.is_not(None),
            )
            .order_by(Publication.published_at.desc())
            .limit(TIME_TO_PUBLISH_SAMPLE)
        )
    ).all()
    gaps = [
        (published_at - created_at).total_seconds()
        for published_at, created_at in gaps_rows
    ]
    ttp = TimeToPublish(
        averageSeconds=statistics.fmean(gaps) if gaps else None,
        medianSeconds=statistics.median(gaps) if gaps else None,
        sampleSize=len(gaps),
    )

    payload = AnalyticsPublishingResponse(success=success, timeToPublish=ttp)
    return envelope(
        payload.model_dump(by_alias=True), request_id=get_request_id(request)
    )
