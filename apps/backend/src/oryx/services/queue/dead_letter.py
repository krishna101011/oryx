"""Dead-letter promotion + cleanup helpers.

Drainer (Batch 2) calls `promote_to_dead_letter()` when:
  - `attempts > MAX_DELIVERY_ATTEMPTS`
  - a handler raises a permanent classification

`run_cleanup()` is the hourly job that prunes delivered outbox rows past
the retention window. It is intentionally a separate function (not a
scheduler config) so it can be invoked from operator runbooks too.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import OutboxDeadLetter, OutboxEvent

MAX_DELIVERY_ATTEMPTS = 20
DELIVERED_RETENTION = timedelta(days=7)
DEAD_LETTER_RETENTION = timedelta(days=90)


async def promote_to_dead_letter(
    session: AsyncSession,
    *,
    row: OutboxEvent,
    final_error: str,
) -> uuid.UUID:
    dl = OutboxDeadLetter(
        id=uuid.uuid4(),
        original_id=row.id,
        event_name=row.event_name,
        event=row.event,
        workspace_id=row.workspace_id,
        final_error=final_error,
        total_attempts=row.attempts,
    )
    session.add(dl)
    await session.execute(delete(OutboxEvent).where(OutboxEvent.id == row.id))
    await session.flush()
    return dl.id


async def run_cleanup(session: AsyncSession, *, now: datetime | None = None) -> dict[str, int]:
    """Delete delivered outbox rows older than DELIVERED_RETENTION,
    and dead-letter rows older than DEAD_LETTER_RETENTION.

    Returns counts for observability.
    """
    now = now or datetime.now(UTC)
    delivered_cutoff = now - DELIVERED_RETENTION
    dl_cutoff = now - DEAD_LETTER_RETENTION

    res1 = await session.execute(
        delete(OutboxEvent).where(
            OutboxEvent.delivered_at.is_not(None),
            OutboxEvent.delivered_at < delivered_cutoff,
        )
    )
    res2 = await session.execute(
        delete(OutboxDeadLetter).where(OutboxDeadLetter.moved_at < dl_cutoff)
    )
    return {
        "outbox_deleted": int(getattr(res1, "rowcount", 0) or 0),
        "dead_letter_deleted": int(getattr(res2, "rowcount", 0) or 0),
    }


async def list_dead_letter(
    session: AsyncSession, *, limit: int = 50
) -> list[OutboxDeadLetter]:
    result = await session.execute(
        select(OutboxDeadLetter).order_by(OutboxDeadLetter.moved_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_dead_letter(
    session: AsyncSession, dead_letter_id: uuid.UUID
) -> OutboxDeadLetter | None:
    return await session.get(OutboxDeadLetter, dead_letter_id)


async def replay_dead_letter(
    session: AsyncSession, *, row: OutboxDeadLetter
) -> uuid.UUID:
    """Move a dead-letter entry back into the outbox with fresh delivery state.

    The envelope (including its event id) is preserved so handler-side
    idempotency keys still apply; only the outbox row id is new, because
    the original row id may exist again after a prior replay was delivered.
    """
    replayed = OutboxEvent(
        id=uuid.uuid4(),
        event_name=row.event_name,
        event=row.event,
        workspace_id=row.workspace_id,
    )
    session.add(replayed)
    await session.execute(
        delete(OutboxDeadLetter).where(OutboxDeadLetter.id == row.id)
    )
    await session.flush()
    return replayed.id


async def discard_dead_letter(
    session: AsyncSession, *, row: OutboxDeadLetter
) -> None:
    await session.execute(
        delete(OutboxDeadLetter).where(OutboxDeadLetter.id == row.id)
    )
    await session.flush()
