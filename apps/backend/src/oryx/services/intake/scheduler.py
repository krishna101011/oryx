"""Intake scheduler — separate-process entry point (CR-7 / ADR-025).

Run:
    python -m oryx.services.intake.scheduler

Each tick: select candidate sources (enabled, pollable kind, status healthy
or degraded), filter to the due ones, and dispatch each to a
SourceSyncRunner task behind a per-kind semaphore so one sick vendor can't
starve the others (§18.2).

Due-time rules (§5.1, §10.2, §10.3):
  - healthy, no failures   → due every `fetch_interval_minutes` (per-kind default)
  - healthy, failing       → due on the exponential backoff curve
  - degraded               → hourly probe only
  - auth_required/disabled → never (user/operator intervention required)
  - last_attempt_at = NULL → due now (new source, or manual sync trigger —
    the router clears the field to request a prompt pull)

The scheduler also hosts the hourly webhook-idempotency purge (§6.4): it
is intake's janitor the same way the drainer is the outbox's.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import IntakeSource
from oryx.services.intake.providers.errors import (
    BACKOFF_CAP_SECONDS,
    BASE_BACKOFF_SECONDS,
)
from oryx.services.intake.providers.webhook.idempotency import (
    WebhookIdempotencyRepository,
)
from oryx.services.intake.sync_runner import SourceSyncRunner

logger = get_logger(__name__)

# webhook is push-only; manual is operator-only — neither is ever polled.
POLLABLE_KINDS = ("gmail", "rss", "api_pull")
DEFAULT_INTERVAL_MINUTES = {"gmail": 15, "rss": 30, "api_pull": 15}

PROBE_INTERVAL = timedelta(hours=1)  # §10.3 — degraded sources get an hourly probe
DEFAULT_TICK_SECONDS = 15.0
DEFAULT_PER_KIND_CONCURRENCY = 4
IDEMPOTENCY_PURGE_INTERVAL_SECONDS = 3600


def fetch_interval(kind: str, config: dict[str, Any]) -> timedelta:
    minutes = config.get("fetch_interval_minutes") or DEFAULT_INTERVAL_MINUTES[kind]
    return timedelta(minutes=int(minutes))


def failure_backoff(consecutive_failures: int) -> timedelta:
    """Same curve as the §10.2 retry classifier, realized as due-time.

    Jitter is intentionally omitted here: the tick cadence plus per-kind
    semaphores already spread vendor calls; deterministic due-times keep
    the function unit-testable.
    """
    return timedelta(
        seconds=min(
            BASE_BACKOFF_SECONDS * (2 ** consecutive_failures),
            BACKOFF_CAP_SECONDS,
        )
    )


def source_is_due(
    *,
    kind: str,
    status: str,
    enabled: bool,
    config: dict[str, Any],
    last_attempt_at: datetime | None,
    consecutive_failures: int,
    now: datetime,
) -> bool:
    if not enabled or kind not in POLLABLE_KINDS:
        return False
    if status in ("auth_required", "disabled"):
        return False
    if last_attempt_at is None:
        return True
    if status == "degraded":
        return last_attempt_at + PROBE_INTERVAL <= now
    if consecutive_failures > 0:
        return last_attempt_at + failure_backoff(consecutive_failures) <= now
    return last_attempt_at + fetch_interval(kind, config) <= now


class IntakeScheduler:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        runner: SourceSyncRunner | None = None,
        per_kind_concurrency: int = DEFAULT_PER_KIND_CONCURRENCY,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        self._sm = sessionmaker
        self._runner = runner or SourceSyncRunner(sessionmaker)
        self._tick_seconds = tick_seconds
        self._semaphores: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_kind_concurrency)
        )

    async def pick_due(self) -> list[tuple[uuid.UUID, str]]:
        """Return (source_id, kind) for every source due right now."""
        now = datetime.now(UTC)
        async with self._sm() as session:
            result = await session.execute(
                select(IntakeSource).where(
                    IntakeSource.deleted_at.is_(None),
                    IntakeSource.enabled.is_(True),
                    IntakeSource.kind.in_(POLLABLE_KINDS),
                    IntakeSource.status.in_(("healthy", "degraded")),
                )
            )
            rows = result.scalars().all()
        return [
            (row.id, row.kind)
            for row in rows
            if source_is_due(
                kind=row.kind,
                status=row.status,
                enabled=row.enabled,
                config=row.config or {},
                last_attempt_at=row.last_attempt_at,
                consecutive_failures=row.consecutive_failures,
                now=now,
            )
        ]

    async def tick(self) -> int:
        due = await self.pick_due()
        if not due:
            return 0
        await asyncio.gather(
            *(self._run_one(source_id, kind) for source_id, kind in due)
        )
        return len(due)

    async def _run_one(self, source_id: uuid.UUID, kind: str) -> None:
        async with self._semaphores[kind]:
            try:
                await self._runner.sync_source(source_id)
            except Exception:
                # records its own failures, so reaching here is a runner bug.
                # One broken source must never kill the scheduler loop.
                logger.exception(
                    "scheduler.sync_crashed",
                    extra={"intake_source_id": str(source_id), "kind": kind},
                )

    async def purge_idempotency_keys(self) -> int:
        async with self._sm() as session:
            deleted = await WebhookIdempotencyRepository(session).purge_expired()
            await session.commit()
        if deleted:
            logger.info("scheduler.idempotency_purged", extra={"deleted": deleted})
        return deleted

    async def run_forever(self) -> None:
        last_purge = datetime.now(UTC)
        while True:
            dispatched = await self.tick()
            if dispatched:
                logger.info("scheduler.tick", extra={"dispatched": dispatched})
            now = datetime.now(UTC)
            if (now - last_purge).total_seconds() >= IDEMPOTENCY_PURGE_INTERVAL_SECONDS:
                await self.purge_idempotency_keys()
                last_purge = now
            await asyncio.sleep(self._tick_seconds)


async def amain() -> None:
    from oryx.config import get_settings
    from oryx.core.db import get_sessionmaker
    from oryx.core.logging import configure_logging

    configure_logging()
    settings = get_settings()
    scheduler = IntakeScheduler(
        get_sessionmaker(),
        per_kind_concurrency=settings.scheduler_per_kind_concurrency,
        tick_seconds=settings.scheduler_tick_seconds,
    )
    logger.info(
        "scheduler.started",
        extra={
            "tick_seconds": settings.scheduler_tick_seconds,
            "per_kind_concurrency": settings.scheduler_per_kind_concurrency,
        },
    )
    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
