"""Outbox drainer — separate-process entry point (CR-7 / ADR-018).

Run:
    python -m anant.services.queue.drainer

This is the *read side* of the outbox pattern. It picks undelivered
`outbox_events` rows in creation order, publishes each envelope to the
EventBus, and marks them delivered. Failures retry with exponential
backoff; rows that exhaust MAX_DELIVERY_ATTEMPTS or raise
`PermanentDeliveryError` are promoted to `outbox_dead_letter` (CR-3).

Delivery is at-least-once by design (ADR-014 §2.5): the publish happens
before the delivered_at commit, so a crash in between redelivers on the
next pass. Handlers MUST be idempotent.

The drainer also hosts the hourly outbox cleanup job — it is the only
process that owns the outbox tables' lifecycle.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from anant.core.logging import get_logger
from anant.core.models import OutboxEvent
from anant.services.queue.bus import EventBus, InProcessBus, event_from_envelope
from anant.services.queue.dead_letter import (
    MAX_DELIVERY_ATTEMPTS,
    promote_to_dead_letter,
    run_cleanup,
)

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 100
BUSY_SLEEP_SECONDS = 1.0
IDLE_SLEEP_SECONDS = 5.0
CLEANUP_INTERVAL_SECONDS = 3600

# Delivery retries are in-process handler calls, so the curve starts much
# tighter than the vendor-facing sync backoff (errors.py): 5s base, 15 min cap.
DELIVERY_BACKOFF_BASE_SECONDS = 5
DELIVERY_BACKOFF_CAP_SECONDS = 15 * 60

MAX_STORED_ERROR_CHARS = 2000


class PermanentDeliveryError(Exception):
    """Raise from a subscriber to send the event straight to dead-letter.

    Use for poison events — payloads that can never be processed no matter
    how many times they retry (schema violation, referenced row hard-gone).
    """


def delivery_backoff(attempts: int) -> timedelta:
    return timedelta(
        seconds=min(
            DELIVERY_BACKOFF_BASE_SECONDS * (2 ** attempts),
            DELIVERY_BACKOFF_CAP_SECONDS,
        )
    )


def row_is_due(
    *, last_attempt_at: datetime | None, attempts: int, now: datetime
) -> bool:
    if last_attempt_at is None:
        return True
    return last_attempt_at + delivery_backoff(attempts) <= now


@dataclass(frozen=True)
class DrainStats:
    fetched: int
    delivered: int
    retried: int
    dead_lettered: int

    @property
    def acted(self) -> int:
        return self.delivered + self.retried + self.dead_lettered


class OutboxDrainer:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        bus: EventBus,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._sm = sessionmaker
        self._bus = bus
        self._batch_size = batch_size

    async def drain_once(self) -> DrainStats:
        """One pass: fetch a batch of undelivered rows, deliver the due ones."""
        now = datetime.now(UTC)
        fetched = delivered = retried = dead_lettered = 0

        async with self._sm() as session:
            result = await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.delivered_at.is_(None))
                .order_by(OutboxEvent.created_at)
                .limit(self._batch_size)
                # Multi-drainer safe even though Phase 3 deploys one: rows a
                # concurrent drainer holds are skipped, never double-published.
                .with_for_update(skip_locked=True)
            )
            rows = list(result.scalars().all())
            for row in rows:
                fetched += 1
                # Backoff is per-row (a function of attempts), which SQL can't
                # express cheaply — filter here. Not-yet-due rows occupy batch
                # slots, which is fine at Phase 3 volume (§18.1).
                if not row_is_due(
                    last_attempt_at=row.last_attempt_at,
                    attempts=row.attempts,
                    now=now,
                ):
                    continue
                outcome = await self._deliver(session, row, now)
                if outcome == "delivered":
                    delivered += 1
                elif outcome == "retried":
                    retried += 1
                else:
                    dead_lettered += 1
            await session.commit()

        return DrainStats(
            fetched=fetched,
            delivered=delivered,
            retried=retried,
            dead_lettered=dead_lettered,
        )

    async def _deliver(
        self, session: AsyncSession, row: OutboxEvent, now: datetime
    ) -> str:
        try:
            await self._bus.publish(event_from_envelope(row.event))
        except PermanentDeliveryError as e:
            await promote_to_dead_letter(
                session, row=row, final_error=_format_error(e)
            )
            logger.error(
                "drainer.dead_lettered",
                extra={"event_id": str(row.id), "event_name": row.event_name,
                       "reason": "permanent", "attempts": row.attempts},
            )
            return "dead_lettered"
        except Exception as e:
            row.attempts += 1
            row.last_error = _format_error(e)
            row.last_attempt_at = now
            if row.attempts >= MAX_DELIVERY_ATTEMPTS:
                await promote_to_dead_letter(
                    session, row=row, final_error=row.last_error
                )
                logger.error(
                    "drainer.dead_lettered",
                    extra={"event_id": str(row.id), "event_name": row.event_name,
                           "reason": "attempts_exhausted", "attempts": row.attempts},
                )
                return "dead_lettered"
            return "retried"

        row.delivered_at = now
        return "delivered"

    async def run_cleanup(self) -> dict[str, int]:
        async with self._sm() as session:
            counts = await run_cleanup(session)
            await session.commit()
        logger.info("drainer.cleanup", extra=counts)
        return counts

    async def run_forever(self) -> None:
        last_cleanup = datetime.now(UTC)
        while True:
            stats = await self.drain_once()
            if stats.dead_lettered or stats.retried:
                logger.warning(
                    "drainer.pass",
                    extra={"delivered": stats.delivered, "retried": stats.retried,
                           "dead_lettered": stats.dead_lettered},
                )
            now = datetime.now(UTC)
            if (now - last_cleanup).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                await self.run_cleanup()
                last_cleanup = now
            await asyncio.sleep(
                BUSY_SLEEP_SECONDS if stats.acted else IDLE_SLEEP_SECONDS
            )


def _format_error(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:MAX_STORED_ERROR_CHARS]


def build_bus() -> EventBus:
    """Construct the bus and register subscribers.

    Subscriber imports stay local: handler modules import
    PermanentDeliveryError from this module, so importing them at the top
    would be circular.
    """
    from anant.core.db import get_sessionmaker
    from anant.services.claims.service import ClaimExtractionHandler
    from anant.services.intake.events_constants import INTAKE_ITEM_RECEIVED

    bus = InProcessBus()
    bus.subscribe(INTAKE_ITEM_RECEIVED, ClaimExtractionHandler(get_sessionmaker()))
    return bus


async def amain() -> None:
    from anant.config import get_settings
    from anant.core.db import get_sessionmaker
    from anant.core.logging import configure_logging

    configure_logging()
    settings = get_settings()
    drainer = OutboxDrainer(
        get_sessionmaker(),
        build_bus(),
        batch_size=settings.drainer_batch_size,
    )
    logger.info("drainer.started", extra={"batch_size": settings.drainer_batch_size})
    await drainer.run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
