"""NotificationDispatcher — Phase 6 Wave A (the missing writer).

Phase 2 shipped the activity_inbox feed and its read API but nothing ever wrote
to it. This is that writer. It is an EventBus subscriber, following the exact
precedent of Phase 4's ObjectConflictProjector (services/intelligence/service.py)
— a handler class registered in build_bus(), driven by the outbox drainer — NOT
a new standalone polling process. (The DigestWorker in Wave B is the standalone
run_forever() worker; the dispatcher reacts to events the drainer already
delivers.)

For each event in the frozen catalog (docs/PHASE_6_ARCHITECTURE.md §2):
  1. resolve every account in the event's workspace (1:1 today, but architected
     as "all accounts in the workspace" per the forward-compatibility note);
  2. map the event to its category + severity (CATALOG below);
  3. look up alert_preferences for (account, category, channel='in_app') —
     a missing row resolves to the shared default (preferences.resolve_frequency);
  4. if enabled: insert an activity_inbox row + a 'notification_created'
     automation_log row; if disabled: insert ONLY a 'suppressed_by_preference'
     automation_log row. All of one event's writes commit in ONE transaction.

Idempotency (the bus contract is at-least-once): UNIQUE(account_id,
triggered_by_event_id) on automation_log is the key, and the dispatcher
short-circuits if a decision row already exists for this (account, event).

Push delivery (channel='push') is intentionally absent — that is Wave C.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import ActivityInbox, AlertPreference, AutomationLog, WorkspaceMember
from oryx.services.activity.preferences import is_enabled, resolve_frequency
from oryx.services.calendar.events.constants import (
    CALENDAR_ENTRY_CANCELLED,
    CALENDAR_ENTRY_SCHEDULED,
)
from oryx.services.conflicts.events.constants import (
    CONFLICT_DETECTED,
    CONFLICT_RESOLVED,
)
from oryx.services.drafts.events.constants import (
    DRAFT_APPROVED,
    DRAFT_CREATED,
    DRAFT_REJECTED,
    DRAFT_UPDATED,
)
from oryx.services.evidence.events.constants import EVIDENCE_COLLECTED
from oryx.services.intake.events_constants import INTAKE_ITEM_RECEIVED
from oryx.services.intelligence.events.constants import (
    OBJECT_CREATED,
    OBJECT_REVIEWED,
    OBJECT_UPDATED,
)
from oryx.services.publishing.events.constants import (
    CONTENT_PUBLISH_FAILED,
    CONTENT_PUBLISHED,
)
from oryx.services.queue.bus import DomainEvent
from oryx.services.verification.events.constants import CLAIM_FAILED

logger = get_logger(__name__)

# Action-taken vocabulary written to automation_log (Wave A subset; push_sent /
# push_failed land in Wave C).
ACTION_NOTIFICATION_CREATED = "notification_created"
ACTION_SUPPRESSED = "suppressed_by_preference"

# in_app is the only channel Phase 6 Wave A dispatches on.
CHANNEL_IN_APP = "in_app"


@dataclass(frozen=True)
class NotificationSpec:
    """How one event type maps onto a feed row."""

    category: str  # an activity_type value: security|system|verification|publishing
    severity: str  # an activity_severity value: info|warning|error
    title: str


# The frozen Section 2 catalog, verbatim. Keys are the REAL event-name constants
# (re-verified against every events/constants.py this wave). Events NOT in this
# map produce no notification — e.g. research.packet.ready (internal Phase 4→5
# handoff) and the verification.claim.extracted/typed/verified pipeline-churn
# events are deliberately excluded, matching the frozen Section 2 table.
CATALOG: dict[str, NotificationSpec] = {
    INTAKE_ITEM_RECEIVED: NotificationSpec("system", "info", "New item ingested"),
    CONFLICT_DETECTED: NotificationSpec("verification", "warning", "Conflict detected"),
    CONFLICT_RESOLVED: NotificationSpec("verification", "info", "Conflict resolved"),
    CLAIM_FAILED: NotificationSpec("verification", "error", "Claim verification failed"),
    EVIDENCE_COLLECTED: NotificationSpec("verification", "info", "Evidence collected"),
    OBJECT_CREATED: NotificationSpec("verification", "info", "Intelligence object created"),
    OBJECT_UPDATED: NotificationSpec("verification", "info", "Intelligence object updated"),
    OBJECT_REVIEWED: NotificationSpec("verification", "info", "Intelligence object reviewed"),
    DRAFT_CREATED: NotificationSpec("publishing", "info", "Draft created"),
    DRAFT_UPDATED: NotificationSpec("publishing", "info", "Draft updated"),
    DRAFT_APPROVED: NotificationSpec("publishing", "info", "Draft approved"),
    DRAFT_REJECTED: NotificationSpec("publishing", "warning", "Draft changes requested"),
    CALENDAR_ENTRY_SCHEDULED: NotificationSpec("publishing", "info", "Post scheduled"),
    CALENDAR_ENTRY_CANCELLED: NotificationSpec("publishing", "info", "Scheduled post cancelled"),
    CONTENT_PUBLISHED: NotificationSpec("publishing", "info", "Content published"),
    CONTENT_PUBLISH_FAILED: NotificationSpec("publishing", "error", "Publishing failed"),
}

# The event names the dispatcher subscribes to (build_bus wires each to it).
SUBSCRIBED_EVENTS: tuple[str, ...] = tuple(CATALOG.keys())


class NotificationDispatcher:
    """Bus subscriber that turns catalog events into activity_inbox rows."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        catalog: dict[str, NotificationSpec] | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._catalog = catalog if catalog is not None else CATALOG

    async def __call__(self, event: DomainEvent) -> None:
        spec = self._catalog.get(event.name)
        if spec is None:
            return  # not a notification-producing event (defensive)
        if event.workspace_id is None:
            # No workspace → no audience to resolve. Nothing to do.
            return

        workspace_id = uuid.UUID(event.workspace_id)
        event_id = uuid.UUID(event.id)

        async with self._sm() as session:
            account_ids = await _accounts_in_workspace(session, workspace_id)
            created = 0
            suppressed = 0
            for account_id in account_ids:
                action = await self._dispatch_for_account(
                    session,
                    account_id=account_id,
                    workspace_id=workspace_id,
                    event=event,
                    event_id=event_id,
                    spec=spec,
                )
                if action == ACTION_NOTIFICATION_CREATED:
                    created += 1
                elif action == ACTION_SUPPRESSED:
                    suppressed += 1
            await session.commit()

        if created or suppressed:
            logger.info(
                "notification.dispatched",
                extra={
                    "event_name": event.name,
                    "event_id": event.id,
                    "created": created,
                    "suppressed": suppressed,
                },
            )

    async def _dispatch_for_account(
        self,
        session: AsyncSession,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        event: DomainEvent,
        event_id: uuid.UUID,
        spec: NotificationSpec,
    ) -> str | None:
        # Idempotency: one decision per (account, event). If we already recorded
        # one (redelivery), do nothing — the UNIQUE constraint is the backstop.
        already = await session.scalar(
            select(AutomationLog.id).where(
                AutomationLog.account_id == account_id,
                AutomationLog.triggered_by_event_id == event_id,
            )
        )
        if already is not None:
            return None

        existing_freq = await session.scalar(
            select(AlertPreference.frequency).where(
                AlertPreference.account_id == account_id,
                AlertPreference.type == spec.category,
                AlertPreference.channel == CHANNEL_IN_APP,
            )
        )
        frequency = resolve_frequency(existing_freq)

        if is_enabled(frequency):
            inbox = ActivityInbox(
                id=uuid.uuid4(),
                account_id=account_id,
                workspace_id=workspace_id,
                type=spec.category,
                severity=spec.severity,
                title=spec.title,
                body=None,
                data=dict(event.payload),
                source_event_type=event.name,
                source_event_id=event_id,
            )
            session.add(inbox)
            await session.flush()
            session.add(
                AutomationLog(
                    id=uuid.uuid4(),
                    account_id=account_id,
                    workspace_id=workspace_id,
                    activity_inbox_id=inbox.id,
                    triggered_by_event_type=event.name,
                    triggered_by_event_id=event_id,
                    action_taken=ACTION_NOTIFICATION_CREATED,
                )
            )
            return ACTION_NOTIFICATION_CREATED

        session.add(
            AutomationLog(
                id=uuid.uuid4(),
                account_id=account_id,
                workspace_id=workspace_id,
                activity_inbox_id=None,
                triggered_by_event_type=event.name,
                triggered_by_event_id=event_id,
                action_taken=ACTION_SUPPRESSED,
            )
        )
        return ACTION_SUPPRESSED


async def _accounts_in_workspace(
    session: AsyncSession, workspace_id: uuid.UUID
) -> list[uuid.UUID]:
    """All active members of the workspace.

    Exactly one row today (the personal-workspace owner), but resolved as a set
    so Team membership (future Phase 2 deepening) needs no dispatcher change.
    """
    result = await session.execute(
        select(WorkspaceMember.account_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    return [row[0] for row in result.all()]
