"""AnalyticsAggregator — Phase 7 Wave A, Source A of the two-source model.

A bus subscriber (registered in build_bus() exactly like
NotificationDispatcher) whose ONLY job is to record that a catalog event
happened: one analytics_events_raw row per delivered event, carrying the
event's workspace_id, name and occurred_at. No preference resolution, no
severity mapping, no fan-out — deliberately nothing beyond "this happened"
(docs/PHASE_7_ARCHITECTURE.md §2, ADR-047).

Idempotency under the bus's at-least-once contract: `source_event_id` is the
envelope's own id (== the outbox row's id, queue/outbox.py), unique in the
table — a redelivered event's insert conflicts and is silently dropped.

Catalog scope: the 20 metric-bearing events of the frozen doc's §3.3, plus
the post-freeze verification.ai.parse_failed extension (2026-07-22 ADR). The two
`workspace.deletion.*` cascade lifecycle events (intake/workspace_cascade.py)
are deliberately NOT subscribed: they are published with workspace_id=None
(the workspace row is mid-deletion), so there is no workspace to attribute a
fact to, and they feed no metric. As a second line of defence, any delivered
event that somehow lacks a workspace_id is skipped with a warning rather than
crashing delivery.
"""
from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import AnalyticsEventRaw
from oryx.services.calendar.events.constants import (
    CALENDAR_ENTRY_CANCELLED,
    CALENDAR_ENTRY_SCHEDULED,
)
from oryx.services.claims.events.constants import CLAIM_EXTRACTED, CLAIM_TYPED
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
from oryx.services.research.events.constants import PACKET_READY
from oryx.services.verification.events.constants import (
    AI_PARSE_FAILED,
    CLAIM_FAILED,
    CLAIM_VERIFIED,
)

from .metrics import EVENT_METRICS

logger = get_logger(__name__)

# The full metric catalog: the frozen doc's §3.3 twenty events plus the
# post-freeze AI_PARSE_FAILED extension (2026-07-22 ADR). Kept as an explicit
# tuple — build_bus() loops over it the same way it does the dispatcher's
# SUBSCRIBED_EVENTS.
ANALYTICS_EVENTS: tuple[str, ...] = (
    INTAKE_ITEM_RECEIVED,
    CLAIM_EXTRACTED,
    CLAIM_TYPED,
    CLAIM_VERIFIED,
    CLAIM_FAILED,
    EVIDENCE_COLLECTED,
    CONFLICT_DETECTED,
    CONFLICT_RESOLVED,
    OBJECT_CREATED,
    OBJECT_UPDATED,
    OBJECT_REVIEWED,
    PACKET_READY,
    DRAFT_CREATED,
    DRAFT_UPDATED,
    DRAFT_APPROVED,
    DRAFT_REJECTED,
    CONTENT_PUBLISHED,
    CONTENT_PUBLISH_FAILED,
    CALENDAR_ENTRY_SCHEDULED,
    CALENDAR_ENTRY_CANCELLED,
    AI_PARSE_FAILED,
)

# Every subscribed event must map to a metric; a mismatch is a wiring bug
# caught at import time, not at the first delivery.
assert set(ANALYTICS_EVENTS) == set(EVENT_METRICS), (
    "ANALYTICS_EVENTS and metrics.EVENT_METRICS have drifted apart"
)


class AnalyticsAggregator:
    """Record-that-it-happened bus handler. Nothing else, by design."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def __call__(self, event) -> None:  # DomainEvent (queue/bus.py)
        if event.workspace_id is None:
            # Not expected for any subscribed event (all 20 publishers pass a
            # real workspace_id) — but a fact without a workspace cannot be
            # recorded, and analytics must never fail a delivery over it.
            logger.warning(
                "analytics.event_without_workspace",
                extra={"event_name": event.name, "event_id": event.id},
            )
            return
        async with self._sm() as session:
            await session.execute(
                pg_insert(AnalyticsEventRaw)
                .values(
                    id=uuid.uuid4(),
                    workspace_id=uuid.UUID(event.workspace_id),
                    source_event_id=uuid.UUID(event.id),
                    event_name=event.name,
                    occurred_at=event.occurred_at,
                )
                # Redelivery (at-least-once contract): the fact is already
                # recorded; conflicting on the envelope id is the no-op path.
                .on_conflict_do_nothing(index_elements=["source_event_id"])
            )
            await session.commit()
