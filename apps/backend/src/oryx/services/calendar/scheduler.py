"""Calendar scheduler — separate-process entry point (CR-7 / ADR-025).

Run:
    python -m oryx.services.calendar.scheduler

Same shape as the intake scheduler and the outbox drainer: a tick loop in a
standalone process, colocatable into the API via oryx_dev_monoprocess in dev.

Each tick runs TWO independent passes (§12.3 / §16.3 / §19.3):

  PASS A — calendar firing. 'scheduled' entries whose scheduled_at has arrived:
    - within the 15-minute grace window  → fire through the EXISTING publishing
      engine (publish_draft); map the per-target result onto the entry
      (delivered → published, failed → failed, pending → leave scheduled for
      Pass B to re-drive).
    - beyond the 15-minute grace window  → mark 'failed' WITHOUT publishing. A
      wildly-late silent publish is worse than a visible miss (§19.3).

  PASS B — transient retry re-drive. Wave D leaves transiently-failed
    publications at status='pending' with an incremented attempt_count, deferring
    "something re-invokes them later" to here. With proper exponential backoff
    (5 min / 30 min / 2 hr), re-invoke publish_draft — the SAME function, which
    already handles the pending row idempotently and advances
    attempt_count/last_attempt_at/status itself.

An immediate pass runs at process startup (not waiting for the first 60s tick)
so overdue work from a downtime period is caught right away.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import CalendarEntry, Publication
from oryx.services.calendar.models import CalendarTickStats
from oryx.services.calendar.repository import CalendarRepository
from oryx.services.drafts.repository import DraftsRepository
from oryx.services.publishing.engine import PublishingEngine
from oryx.services.publishing.repository import PublicationsRepository

logger = get_logger(__name__)

DEFAULT_TICK_SECONDS = 60.0

# §19.3 — an entry the scheduler reaches more than this late is marked failed
# WITHOUT publishing (a visible miss beats a wildly-late silent publish).
GRACE_WINDOW = timedelta(minutes=15)

# §16.3 — exponential backoff keyed by the publication's CURRENT attempt_count,
# i.e. how long to wait before the NEXT attempt. Tiers 1→2, 2→3, 3→4 are the
# frozen schedule; a row already at attempt_count 4 (awaiting its 5th and final
# attempt before Wave D's at-5 failure) reuses the 2-hour interval so it is never
# stranded pending. Reaching attempt_count 5 is Wave D's terminal 'failed'.
RETRY_BACKOFF: dict[int, timedelta] = {
    1: timedelta(minutes=5),
    2: timedelta(minutes=30),
    3: timedelta(hours=2),
    4: timedelta(hours=2),
}


def within_grace(*, scheduled_at: datetime, now: datetime) -> bool:
    """True while a due entry is still inside the 15-minute grace window."""
    return scheduled_at > now - GRACE_WINDOW


def retry_due(
    *, attempt_count: int, last_attempt_at: datetime | None, now: datetime
) -> bool:
    """True when a pending publication has waited out its backoff interval."""
    backoff = RETRY_BACKOFF.get(attempt_count)
    if backoff is None:
        return False
    if last_attempt_at is None:
        # A pending row with attempts but no recorded time (pre-Wave-E row): do
        # not strand it — treat as due.
        return True
    return last_attempt_at + backoff <= now


class CalendarScheduler:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        engine: PublishingEngine | None = None,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        self._sm = sessionmaker
        self._engine = engine or PublishingEngine(sessionmaker)
        self._tick_seconds = tick_seconds

    # ---------------- Pass A: calendar firing ----------------

    async def fire_due_entries(self, now: datetime) -> int:
        async with self._sm() as session:
            due = await CalendarRepository(session).due_scheduled(now)
        fired = 0
        for entry in due:
            try:
                await self._fire_one(entry, now)
                fired += 1
            except Exception:
                # One bad entry (e.g. its draft was hard-deleted) must never kill
                # the loop. The entry stays 'scheduled' and is retried next tick.
                logger.exception(
                    "calendar.fire_crashed",
                    extra={"calendar_entry_id": str(entry.id)},
                )
        return fired

    async def _fire_one(self, entry: CalendarEntry, now: datetime) -> None:
        if not within_grace(scheduled_at=entry.scheduled_at, now=now):
            # Beyond grace: mark failed WITHOUT calling publish_draft (§19.3).
            await self._set_entry_status(entry.id, "failed")
            logger.warning(
                "calendar.missed_grace",
                extra={
                    "calendar_entry_id": str(entry.id),
                    "scheduled_at": entry.scheduled_at.isoformat(),
                },
            )
            return

        results = await self._engine.publish_draft(
            draft_id=entry.draft_id,
            target_ids=[entry.target_id],
            workspace_id=entry.workspace_id,
            account_id=entry.created_by,
        )
        result = next(
            (r for r in results if r.target_id == entry.target_id), None
        )
        if result is None:
            return
        if result.status == "delivered":
            await self._set_entry_status(
                entry.id, "published", publication_id=result.publication_id
            )
        elif result.status == "failed":
            await self._set_entry_status(entry.id, "failed")
        # 'pending' (transient): leave the entry 'scheduled' — Pass B re-drives
        # the underlying publication, and the entry resolves on a later tick.

    async def _set_entry_status(
        self,
        entry_id: uuid.UUID,
        status: str,
        *,
        publication_id: uuid.UUID | None = None,
    ) -> None:
        async with self._sm() as session:
            await CalendarRepository(session).set_status(
                entry_id=entry_id, status=status, publication_id=publication_id
            )
            await session.commit()

    # ---------------- Pass B: transient retry re-drive ----------------

    async def redrive_pending(self, now: datetime) -> int:
        async with self._sm() as session:
            candidates = await PublicationsRepository(session).list_retry_candidates()
        redriven = 0
        for pub in candidates:
            if not retry_due(
                attempt_count=pub.attempt_count,
                last_attempt_at=pub.last_attempt_at,
                now=now,
            ):
                continue
            try:
                await self._redrive_one(pub)
                redriven += 1
            except Exception:
                logger.exception(
                    "calendar.redrive_crashed",
                    extra={"publication_id": str(pub.id)},
                )
        return redriven

    async def _redrive_one(self, pub: Publication) -> None:
        # publish_draft needs an actor; use the draft owner for the system-driven
        # retry. The engine itself advances attempt_count/last_attempt_at/status.
        async with self._sm() as session:
            draft = await DraftsRepository(session).get_draft(
                workspace_id=pub.workspace_id, draft_id=pub.draft_id
            )
        if draft is None:
            return
        await self._engine.publish_draft(
            draft_id=pub.draft_id,
            target_ids=[pub.target_id],
            workspace_id=pub.workspace_id,
            account_id=draft.account_id,
        )

    # ---------------- tick / loop ----------------

    async def tick(self) -> CalendarTickStats:
        now = datetime.now(UTC)
        fired = await self.fire_due_entries(now)
        redriven = await self.redrive_pending(now)
        return CalendarTickStats(fired=fired, redriven=redriven)

    async def run_forever(self) -> None:
        # The first tick happens immediately (startup catch-up), BEFORE any sleep,
        # so a downtime backlog is processed without waiting a full interval.
        while True:
            stats = await self.tick()
            if stats.acted:
                logger.info(
                    "calendar.tick",
                    extra={"fired": stats.fired, "redriven": stats.redriven},
                )
            await asyncio.sleep(self._tick_seconds)


async def amain() -> None:
    from oryx.core.db import get_sessionmaker
    from oryx.core.logging import configure_logging

    configure_logging()
    scheduler = CalendarScheduler(get_sessionmaker())
    logger.info("calendar_scheduler.started", extra={"tick_seconds": DEFAULT_TICK_SECONDS})
    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
