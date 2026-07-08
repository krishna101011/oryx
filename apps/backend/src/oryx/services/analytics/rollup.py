"""RollupWorker — Phase 7 Wave A: the periodic rollup-refresh worker.

Run:
    python -m oryx.services.analytics.rollup

Same standalone tick-loop shape as the DigestWorker (ADR-025 topology; the
first tick fires immediately as the startup catch-up), colocatable via
oryx_dev_monoprocess=1 like the other four workers (main.py lifespan).

Each tick RECOMPUTES — never increments — every (workspace, metric, UTC day)
value present in the sources and upserts it into analytics_rollups_daily
(ADR-047):

- Source A: GROUP BY over analytics_events_raw (the AnalyticsAggregator's
  facts). History here starts at Wave A ship time by construction — the table
  only contains what the subscriber recorded, so no pre-ship day can ever
  appear; nothing is invented retroactively.
- Source B: GROUP BY over automation_log (per real action_taken value) and
  digest_runs (rows = sent digests; account-scoped, attributed to workspaces
  via workspace_members). These tables carry their full Phase 6 history, so
  the FIRST tick backfills every historical day they already cover — that
  data exists and costs nothing to surface.

The rollup table is SPARSE: a (workspace, metric, day) with zero activity
writes no row. Zero-days would multiply rows by |metrics| x |days| x
|workspaces| for no informational gain (absence of a row IS the zero); and
because the sources are append-only, a recomputed value can never shrink to
zero after having been non-zero, so no stale row is ever left behind by
skipping zeros. Recomputing the full history every tick is deliberate: the
sources are small at current volume, and statelessness is what makes the
refresh trivially idempotent — the same tick run twice (or two ticks racing)
converges on identical values.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import (
    AnalyticsEventRaw,
    AnalyticsRollupDaily,
    AutomationLog,
    DigestRun,
    WorkspaceMember,
)

from .metrics import ACTION_METRICS, EVENT_METRICS, METRIC_DIGESTS_SENT

logger = get_logger(__name__)

DEFAULT_TICK_SECONDS = 300.0


def _utc_day(column):
    """UTC calendar-day bucket for a timestamptz column, session-TZ-proof."""
    return cast(func.timezone("UTC", column), Date)


class RollupWorker:
    """Tick loop that refreshes analytics_rollups_daily from both sources."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        self._sm = sessionmaker
        self._tick_seconds = tick_seconds

    async def tick(self) -> int:
        """Recompute every present (workspace, metric, day); return rows upserted."""
        async with self._sm() as session:
            rows = (
                await self._source_a(session)
                + await self._source_b_automation(session)
                + await self._source_b_digests(session)
            )
            if rows:
                stmt = pg_insert(AnalyticsRollupDaily).values(rows)
                await session.execute(
                    stmt.on_conflict_do_update(
                        constraint="uq_analytics_rollups_ws_metric_date",
                        set_={
                            "value": stmt.excluded.value,
                            "updated_at": func.now(),
                        },
                    )
                )
            await session.commit()
        return len(rows)

    async def _source_a(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(
                AnalyticsEventRaw.workspace_id,
                AnalyticsEventRaw.event_name,
                _utc_day(AnalyticsEventRaw.occurred_at).label("day"),
                func.count().label("n"),
            ).group_by(
                AnalyticsEventRaw.workspace_id,
                AnalyticsEventRaw.event_name,
                "day",
            )
        )
        return [
            {
                "workspace_id": row.workspace_id,
                "metric_key": EVENT_METRICS[row.event_name],
                "date": row.day,
                "value": row.n,
            }
            for row in result.all()
            # Unknown names can't be inserted by the aggregator (its catalog
            # is import-time-checked against EVENT_METRICS) — but a manually
            # inserted stray row must not crash every future refresh.
            if row.event_name in EVENT_METRICS
        ]

    async def _source_b_automation(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(
                AutomationLog.workspace_id,
                AutomationLog.action_taken,
                _utc_day(AutomationLog.created_at).label("day"),
                func.count().label("n"),
            ).group_by(
                AutomationLog.workspace_id,
                AutomationLog.action_taken,
                "day",
            )
        )
        # ACTION_METRICS includes push_suppressed_quiet_hours, which no
        # dispatcher code writes yet — it simply never comes back from this
        # GROUP BY, so the metric reads as absent (zero) until the Phase 6
        # logging addendum lands. Unknown FUTURE action values are skipped
        # rather than crashing the worker.
        return [
            {
                "workspace_id": row.workspace_id,
                "metric_key": ACTION_METRICS[row.action_taken],
                "date": row.day,
                "value": row.n,
            }
            for row in result.all()
            if row.action_taken in ACTION_METRICS
        ]

    async def _source_b_digests(self, session: AsyncSession) -> list[dict]:
        # digest_runs is account-scoped (a digest bundle can span workspaces),
        # so attribution goes through workspace_members: each workspace the
        # account belongs to counts the digest. Exact while accounts hold one
        # membership (today's reality); documented approximation beyond that
        # (ADR-047).
        result = await session.execute(
            select(
                WorkspaceMember.workspace_id,
                _utc_day(DigestRun.sent_at).label("day"),
                func.count().label("n"),
            )
            .join(WorkspaceMember, WorkspaceMember.account_id == DigestRun.account_id)
            .group_by(WorkspaceMember.workspace_id, "day")
        )
        return [
            {
                "workspace_id": row.workspace_id,
                "metric_key": METRIC_DIGESTS_SENT,
                "date": row.day,
                "value": row.n,
            }
            for row in result.all()
        ]

    async def run_forever(self) -> None:
        # The first tick happens immediately (startup catch-up), BEFORE any
        # sleep — same contract as the other four workers. For this worker the
        # catch-up IS the Source B historical backfill on first ever run.
        while True:
            upserted = await self.tick()
            if upserted:
                logger.info("analytics.rollup_tick", extra={"rows_upserted": upserted})
            await asyncio.sleep(self._tick_seconds)


async def amain() -> None:
    from oryx.core.db import get_sessionmaker
    from oryx.core.logging import configure_logging

    configure_logging()
    worker = RollupWorker(get_sessionmaker())
    logger.info(
        "rollup_worker.started", extra={"tick_seconds": DEFAULT_TICK_SECONDS}
    )
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
