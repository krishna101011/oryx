"""Calendar-entries repository — DB operations only, no business rules.

The only place that touches the calendar_entries table. Scheduling rules
(status promotion, grace window, backoff) live in the service / scheduler.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import CalendarEntry


class CalendarRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def insert_entry(
        self,
        *,
        workspace_id: uuid.UUID,
        draft_id: uuid.UUID,
        target_id: uuid.UUID,
        scheduled_at: datetime,
        created_by: uuid.UUID,
    ) -> CalendarEntry | None:
        """Insert a scheduled entry. ON CONFLICT (draft_id, target_id) DO NOTHING:
        a duplicate schedule returns None, and the service surfaces a clean error
        instead of leaking the raw constraint violation."""
        stmt = (
            pg_insert(CalendarEntry)
            .values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                draft_id=draft_id,
                target_id=target_id,
                scheduled_at=scheduled_at,
                status="scheduled",
                created_by=created_by,
            )
            .on_conflict_do_nothing(
                constraint="uq_calendar_entries_draft_target"
            )
            .returning(CalendarEntry.id)
        )
        new_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if new_id is None:
            return None
        return await self.db.get(CalendarEntry, new_id)

    async def get_entry(
        self, *, workspace_id: uuid.UUID, entry_id: uuid.UUID
    ) -> CalendarEntry | None:
        result = await self.db.execute(
            select(CalendarEntry).where(
                CalendarEntry.id == entry_id,
                CalendarEntry.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_in_range(
        self,
        *,
        workspace_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEntry]:
        result = await self.db.execute(
            select(CalendarEntry)
            .where(
                CalendarEntry.workspace_id == workspace_id,
                CalendarEntry.scheduled_at >= start,
                CalendarEntry.scheduled_at <= end,
            )
            .order_by(CalendarEntry.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def count_scheduled_for_draft(self, draft_id: uuid.UUID) -> int:
        """Number of still-'scheduled' entries for a draft. Called after a
        cancel's UPDATE has flushed, so the just-cancelled row is NOT counted."""
        result = await self.db.execute(
            select(func.count())
            .select_from(CalendarEntry)
            .where(
                CalendarEntry.draft_id == draft_id,
                CalendarEntry.status == "scheduled",
            )
        )
        return int(result.scalar_one())

    async def set_status(
        self,
        *,
        entry_id: uuid.UUID,
        status: str,
        publication_id: uuid.UUID | None = None,
    ) -> None:
        values: dict[str, object] = {"status": status}
        if publication_id is not None:
            values["publication_id"] = publication_id
        await self.db.execute(
            update(CalendarEntry)
            .where(CalendarEntry.id == entry_id)
            .values(**values)
        )

    async def due_scheduled(self, now: datetime) -> list[CalendarEntry]:
        """All workspaces' 'scheduled' entries whose time has arrived. Backed by
        the partial index idx_calendar_scheduled (status='scheduled'). The grace
        window is applied per-row by the scheduler, not in SQL."""
        result = await self.db.execute(
            select(CalendarEntry)
            .where(
                CalendarEntry.status == "scheduled",
                CalendarEntry.scheduled_at <= now,
            )
            .order_by(CalendarEntry.scheduled_at.asc())
        )
        return list(result.scalars().all())
