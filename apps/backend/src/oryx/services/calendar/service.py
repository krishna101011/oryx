"""Calendar service (§12.3 / §7.2) — schedule, cancel, and list calendar entries.

A calendar entry is an analyst's explicit decision to publish an approved draft
to one target at a future time. The CalendarScheduler fires them; this service
owns only the CRUD + the draft-status interaction:

  - Scheduling the FIRST entry for a draft promotes it 'approved' → 'scheduled'.
    Scheduling additional targets while already 'scheduled' does NOT change
    status further.
  - Cancelling an entry reverts the draft to 'approved' ONLY if no other
    'scheduled' entries remain — and never regresses a draft that has already
    reached 'published' via some other target firing first.

Each public method is ONE transaction.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import (
    BadRequestError,
    NotFoundError,
    PreconditionFailedError,
)
from oryx.core.logging import get_logger
from oryx.core.models import CalendarEntry
from oryx.services.calendar.events.constants import (
    CALENDAR_ENTRY_CANCELLED,
    CALENDAR_ENTRY_SCHEDULED,
)
from oryx.services.calendar.repository import CalendarRepository
from oryx.services.drafts.repository import DraftsRepository
from oryx.services.queue.outbox import enqueue_event
from oryx.services.targets.repository import TargetsRepository

logger = get_logger(__name__)

# A draft can be scheduled only from these statuses (approved, or already
# scheduled for another target).
_SCHEDULABLE_DRAFT_STATUSES = ("approved", "scheduled")


def _as_utc(dt: datetime) -> datetime:
    """Normalise a (possibly naive) datetime to aware UTC for safe comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class CalendarService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def schedule_draft(
        self,
        *,
        draft_id: uuid.UUID,
        target_id: uuid.UUID,
        scheduled_at: datetime,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> CalendarEntry:
        scheduled_at = _as_utc(scheduled_at)
        async with self._sm() as session:
            drafts = DraftsRepository(session)
            targets = TargetsRepository(session)
            cal = CalendarRepository(session)

            # 1+2. Draft must exist (in this workspace) and be schedulable.
            draft = await drafts.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if draft is None:
                raise NotFoundError("Draft not found")
            if draft.status not in _SCHEDULABLE_DRAFT_STATUSES:
                raise PreconditionFailedError(
                    "Only an approved (or already-scheduled) draft can be "
                    "scheduled",
                    details={"status": draft.status},
                )

            # 3. Target must exist (in this workspace) and be active.
            target = await targets.get(
                workspace_id=workspace_id, target_id=target_id
            )
            if target is None:
                raise NotFoundError("Publish target not found")
            if not target.is_active:
                raise PreconditionFailedError(
                    "Publish target is not active",
                    details={"targetId": str(target_id)},
                )

            # 4. The scheduled time must be in the future.
            if scheduled_at <= datetime.now(UTC):
                raise BadRequestError("scheduled time must be in the future")

            # 5. Insert (ON CONFLICT surfaces a clean duplicate error).
            entry = await cal.insert_entry(
                workspace_id=workspace_id,
                draft_id=draft_id,
                target_id=target_id,
                scheduled_at=scheduled_at,
                created_by=account_id,
            )
            if entry is None:
                raise PreconditionFailedError(
                    "This target is already scheduled for this draft",
                    details={"draftId": str(draft_id), "targetId": str(target_id)},
                )

            # 6. Promote approved → scheduled (only on the first entry).
            if draft.status == "approved":
                await drafts.set_draft_status(
                    draft_id=draft_id, status="scheduled"
                )

            # 7. Emit the scheduled event (same transaction).
            await enqueue_event(
                session,
                name=CALENDAR_ENTRY_SCHEDULED,
                payload={
                    "calendarEntryId": str(entry.id),
                    "draftId": str(draft_id),
                    "targetId": str(target_id),
                    "workspaceId": str(workspace_id),
                    "scheduledAt": scheduled_at.isoformat(),
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await cal.get_entry(
                workspace_id=workspace_id, entry_id=entry.id
            )
            assert refreshed is not None
            return refreshed

    async def cancel_entry(
        self,
        *,
        entry_id: uuid.UUID,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> CalendarEntry:
        async with self._sm() as session:
            cal = CalendarRepository(session)
            drafts = DraftsRepository(session)

            # 1. Entry must exist (in this workspace) and still be scheduled.
            entry = await cal.get_entry(
                workspace_id=workspace_id, entry_id=entry_id
            )
            if entry is None:
                raise NotFoundError("Calendar entry not found")
            if entry.status != "scheduled":
                raise PreconditionFailedError(
                    "Only a scheduled calendar entry can be cancelled",
                    details={"status": entry.status},
                )
            draft_id = entry.draft_id

            # 2. Soft-cancel (status only; the row is retained).
            await cal.set_status(entry_id=entry_id, status="cancelled")

            # 3. Revert the draft to 'approved' ONLY if no other scheduled
            #    entries remain AND the draft is still 'scheduled' (never regress
            #    a draft already 'published' by another target firing first).
            remaining = await cal.count_scheduled_for_draft(draft_id)
            draft = await drafts.get_draft(
                workspace_id=workspace_id, draft_id=draft_id
            )
            if remaining == 0 and draft is not None and draft.status == "scheduled":
                await drafts.set_draft_status(
                    draft_id=draft_id, status="approved"
                )

            # 4. Emit the cancellation event (Wave E extension).
            await enqueue_event(
                session,
                name=CALENDAR_ENTRY_CANCELLED,
                payload={
                    "calendarEntryId": str(entry_id),
                    "draftId": str(draft_id),
                    "targetId": str(entry.target_id),
                    "workspaceId": str(workspace_id),
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
                correlation_id=correlation_id,
            )
            await session.commit()
            refreshed = await cal.get_entry(
                workspace_id=workspace_id, entry_id=entry_id
            )
            assert refreshed is not None
            return refreshed

    async def list_calendar(
        self,
        *,
        workspace_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEntry]:
        async with self._sm() as session:
            return await CalendarRepository(session).list_in_range(
                workspace_id=workspace_id,
                start=_as_utc(start_date),
                end=_as_utc(end_date),
            )
