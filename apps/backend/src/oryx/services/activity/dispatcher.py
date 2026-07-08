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
triggered_by_event_id, channel) on automation_log is the key, and the
dispatcher short-circuits per channel if a decision row already exists for
this (account, event, channel).

Push delivery (Wave C) runs as its own SEPARATE step per account, strictly
AFTER the in_app inbox+automation_log transaction has committed — a push
failure can never roll back the notification itself:
  5. resolve the (account, category, channel='push') preference with the same
     shared-default logic as in_app;
  6. if enabled, evaluate quiet_hours (services/activity/quiet_hours.py) — a
     send inside the account's quiet window is silently skipped for this
     event (deliberately no log row; the §3.3 push vocabulary is only
     push_sent/push_failed);
  7. otherwise call the real provider (providers/push/factory.py, gated by
     PUSH_PROVIDER) for each active alert_devices token, holding NO db
     transaction across the HTTP call, and commit ONE new automation_log row
     (channel='push', action push_sent/push_failed) in its own transaction.
     No registered device counts as a failure (push_failed, reason logged),
     never a silent skip.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import (
    ActivityInbox,
    AlertDevice,
    AlertPreference,
    AutomationLog,
    WorkspaceMember,
)
from oryx.services.activity.preferences import is_enabled, resolve_frequency
from oryx.services.activity.providers.push.base import (
    ProviderErrorKind,
    ProviderResult,
    PushMessage,
    PushProvider,
)
from oryx.services.activity.providers.push.factory import get_push_provider
from oryx.services.activity.quiet_hours import is_quiet_now
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

# Action-taken vocabulary written to automation_log (frozen §3.3).
ACTION_NOTIFICATION_CREATED = "notification_created"
ACTION_SUPPRESSED = "suppressed_by_preference"
ACTION_PUSH_SENT = "push_sent"
ACTION_PUSH_FAILED = "push_failed"

# The channels the dispatcher delivers on (email remains out of scope).
CHANNEL_IN_APP = "in_app"
CHANNEL_PUSH = "push"


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
        push_provider_factory: Callable[[str], PushProvider] | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._catalog = catalog if catalog is not None else CATALOG
        # Injectable for tests (fake providers); defaults to the PUSH_PROVIDER-
        # gated factory, resolved per device platform at send time.
        self._push_provider_factory = (
            push_provider_factory if push_provider_factory is not None
            else get_push_provider
        )

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

        # Wave C: push delivery, strictly AFTER the in_app transaction above
        # has committed and in transactions of its own — a failure anywhere in
        # this step can never take the notification row with it. The step is
        # self-idempotent (its own push-slot check), so it runs for every
        # member on every delivery.
        for account_id in account_ids:
            try:
                await self._push_for_account(
                    account_id=account_id,
                    workspace_id=workspace_id,
                    event=event,
                    event_id=event_id,
                    spec=spec,
                )
            except Exception:
                # Push is best-effort; the inbox row already landed.
                logger.exception(
                    "push.step_crashed",
                    extra={"account_id": str(account_id), "event_id": event.id},
                )

        if created or suppressed:
            logger.info(
                "notification.dispatched",
                extra={
                    "event_name": event.name,
                    "event_id": event.id,
                    # NOT "created" — that is a reserved LogRecord attribute and
                    # stdlib logging raises KeyError on any extra key that
                    # shadows one.
                    "notifications_created": created,
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
        # Idempotency: one in_app decision per (account, event). If we already
        # recorded one (redelivery), do nothing — the UNIQUE constraint is the
        # backstop. Scoped to this channel: the push slot is checked separately
        # by _push_for_account.
        already = await session.scalar(
            select(AutomationLog.id).where(
                AutomationLog.account_id == account_id,
                AutomationLog.triggered_by_event_id == event_id,
                AutomationLog.channel == CHANNEL_IN_APP,
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
                    channel=CHANNEL_IN_APP,
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
                channel=CHANNEL_IN_APP,
            )
        )
        return ACTION_SUPPRESSED

    async def _push_for_account(
        self,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        event: DomainEvent,
        event_id: uuid.UUID,
        spec: NotificationSpec,
    ) -> None:
        """The Wave C push step — runs after the in_app transaction committed.

        Reads (one short session), then calls the provider with NO transaction
        open, then writes its one decision row (a second short session). Quiet-
        hours suppression is deliberately silent: the frozen §3.3 push
        vocabulary is push_sent/push_failed only, and the in_app decision row
        already recorded the event's dispatch outcome.
        """
        async with self._sm() as session:
            pref = (
                await session.execute(
                    select(AlertPreference.frequency, AlertPreference.quiet_hours).where(
                        AlertPreference.account_id == account_id,
                        AlertPreference.type == spec.category,
                        AlertPreference.channel == CHANNEL_PUSH,
                    )
                )
            ).one_or_none()
            frequency = resolve_frequency(pref.frequency if pref else None)
            if not is_enabled(frequency):
                return  # push disabled for this category: no push decision row

            # Idempotency: one push decision per (account, event) — same
            # redelivery contract as the in_app slot.
            already = await session.scalar(
                select(AutomationLog.id).where(
                    AutomationLog.account_id == account_id,
                    AutomationLog.triggered_by_event_id == event_id,
                    AutomationLog.channel == CHANNEL_PUSH,
                )
            )
            if already is not None:
                return

            if is_quiet_now(pref.quiet_hours if pref else None):
                logger.info(
                    "push.suppressed_quiet_hours",
                    extra={"account_id": str(account_id), "event_id": event.id},
                )
                return

            devices = (
                (
                    await session.execute(
                        select(AlertDevice).where(
                            AlertDevice.account_id == account_id,
                            AlertDevice.disabled_at.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            # The push row links back to the feed row this event produced for
            # this account (None when in_app was suppressed but push is on).
            inbox_id = await session.scalar(
                select(ActivityInbox.id).where(
                    ActivityInbox.account_id == account_id,
                    ActivityInbox.source_event_id == event_id,
                )
            )
        # Session is CLOSED here — no transaction spans the provider HTTP call.

        if not devices:
            ok = False
            failure_reason = "no_registered_device"
        else:
            results: list[ProviderResult] = []
            for device in devices:
                provider = self._push_provider_factory(device.platform)
                try:
                    result = await provider.send(
                        PushMessage(
                            token=device.push_token,
                            title=spec.title,
                            body="",
                            data={
                                "category": spec.category,
                                "severity": spec.severity,
                                "event_type": event.name,
                                "event_id": event.id,
                                "activity_inbox_id": str(inbox_id or ""),
                            },
                        )
                    )
                except Exception as exc:  # a provider bug must not kill dispatch
                    result = ProviderResult(
                        ok=False,
                        provider=getattr(provider, "name", "unknown"),
                        error_kind=ProviderErrorKind.UNKNOWN,
                        error_message=str(exc),
                    )
                results.append(result)
            # One decision row per event: delivered to at least one device
            # counts as sent; zero deliveries is a failure.
            ok = any(r.ok for r in results)
            failure_reason = "; ".join(
                f"{r.provider}: {r.error_message or r.error_kind}"
                for r in results
                if not r.ok
            )

        async with self._sm() as session:
            session.add(
                AutomationLog(
                    id=uuid.uuid4(),
                    account_id=account_id,
                    workspace_id=workspace_id,
                    activity_inbox_id=inbox_id,
                    triggered_by_event_type=event.name,
                    triggered_by_event_id=event_id,
                    action_taken=ACTION_PUSH_SENT if ok else ACTION_PUSH_FAILED,
                    channel=CHANNEL_PUSH,
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                # Lost a race with a concurrent redelivery: that delivery's
                # decision row is the real one.
                await session.rollback()
                return

        if ok:
            logger.info(
                "push.sent",
                extra={
                    "account_id": str(account_id),
                    "event_id": event.id,
                    "devices": len(devices),
                },
            )
        else:
            logger.warning(
                "push.failed",
                extra={
                    "account_id": str(account_id),
                    "event_id": event.id,
                    "reason": failure_reason,
                },
            )


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
