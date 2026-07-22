"""AnalyticsAggregator — Phase 7 Wave A coverage (Source A of ADR-047).

FROZEN_CATALOG below is the complete 20-event metric catalog from
docs/PHASE_7_ARCHITECTURE.md §3.3 (Rev 2.1) plus its documented post-freeze
extensions, deliberately duplicated here as literals rather than imported
from the aggregator — the test checks the code against the frozen document,
not against itself (same principle as test_notification_dispatcher.py's
catalog table).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db

# (event_name, expected metric key) — frozen doc §3.3, verbatim.
FROZEN_CATALOG: tuple[tuple[str, str], ...] = (
    ("intake.item.received", "intake_items_received"),
    ("verification.claim.extracted", "claims_extracted"),
    ("verification.claim.typed", "claims_typed"),
    ("verification.claim.verified", "claims_verified"),
    ("verification.claim.failed", "claims_failed"),
    ("verification.evidence.collected", "evidence_collected"),
    ("verification.conflict.detected", "conflicts_detected"),
    ("verification.conflict.resolved", "conflicts_resolved"),
    ("intelligence.object.created", "intelligence_objects_created"),
    ("intelligence.object.updated", "intelligence_objects_updated"),
    ("intelligence.object.reviewed", "intelligence_objects_reviewed"),
    ("research.packet.ready", "research_packets_ready"),
    ("content.draft.created", "drafts_created"),
    ("content.draft.updated", "drafts_updated"),
    ("content.draft.approved", "drafts_approved"),
    ("content.draft.rejected", "drafts_rejected"),
    ("content.published", "drafts_published"),
    ("content.publish.failed", "publish_failures"),
    ("content.draft.scheduled", "drafts_scheduled"),
    ("content.calendar.cancelled", "calendar_cancellations"),
    # Post-freeze §3.3 extension (2026-07-22 ADR): AI parse-failure quality
    # signal — same precedent as push_suppressed_quiet_hours (2026-07-08) and
    # the email family (2026-07-21).
    ("verification.ai.parse_failed", "ai_parse_failures_total"),
)


async def _seed_workspace(sm) -> dict:
    from oryx.core.models import Account, Workspace, WorkspaceMember

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"analytics+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Analytics WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id, account_id=account.id, role="owner"
            )
        )
        await session.commit()
        return {"workspace": workspace.id, "account": account.id}


def _event(name: str, *, workspace_id, event_id: uuid.UUID | None = None):
    """A DomainEvent as the drainer would deliver it."""
    from oryx.services.queue.bus import DomainEvent

    now = datetime.now(UTC)
    return DomainEvent(
        id=str(event_id or uuid.uuid4()),
        name=name,
        version=1,
        occurred_at=now,
        emitted_at=now,
        workspace_id=str(workspace_id) if workspace_id is not None else None,
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={},
    )


def _aggregator(sm):
    from oryx.services.analytics.aggregator import AnalyticsAggregator

    return AnalyticsAggregator(sm)


async def _raw_rows(sm, workspace_id):
    from oryx.core.models import AnalyticsEventRaw

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(AnalyticsEventRaw).where(
                        AnalyticsEventRaw.workspace_id == workspace_id
                    )
                )
            )
            .scalars()
            .all()
        )


def test_subscribed_tuple_matches_frozen_catalog() -> None:
    """The aggregator subscribes to exactly the frozen 20 plus the one
    post-freeze extension — no more, no less."""
    from oryx.services.analytics.aggregator import ANALYTICS_EVENTS

    assert sorted(ANALYTICS_EVENTS) == sorted(name for name, _ in FROZEN_CATALOG)
    assert len(ANALYTICS_EVENTS) == 21


# --- Mandatory scenario 1: every catalog event -> exactly one fact row ---


@pytest.mark.asyncio
@pytest.mark.parametrize("event_name", [name for name, _ in FROZEN_CATALOG])
async def test_each_catalog_event_records_exactly_one_fact_row(
    sm, event_name: str
) -> None:
    ids = await _seed_workspace(sm)
    event = _event(event_name, workspace_id=ids["workspace"])

    await _aggregator(sm)(event)

    rows = await _raw_rows(sm, ids["workspace"])
    assert len(rows) == 1
    assert rows[0].event_name == event_name
    assert rows[0].workspace_id == ids["workspace"]
    assert rows[0].source_event_id == uuid.UUID(event.id)
    assert rows[0].occurred_at == event.occurred_at


# --- Mandatory scenario 2: redelivery is a safe no-op ---


@pytest.mark.asyncio
async def test_redelivered_event_does_not_duplicate_the_fact(sm) -> None:
    ids = await _seed_workspace(sm)
    event_id = uuid.uuid4()
    aggregator = _aggregator(sm)

    # Same envelope id both times — the at-least-once redelivery case.
    await aggregator(
        _event("intake.item.received", workspace_id=ids["workspace"], event_id=event_id)
    )
    await aggregator(
        _event("intake.item.received", workspace_id=ids["workspace"], event_id=event_id)
    )

    rows = await _raw_rows(sm, ids["workspace"])
    assert len(rows) == 1
    assert rows[0].source_event_id == event_id


# --- Defensive guard: an event without a workspace is skipped, not a crash ---


@pytest.mark.asyncio
async def test_event_without_workspace_is_skipped_safely(sm) -> None:
    """The workspace.deletion.* lifecycle events publish workspace_id=None and
    are outside the subscribed catalog — but even if such an event reached the
    handler, it must skip (no row, no exception), never fail the delivery."""
    from oryx.core.models import AnalyticsEventRaw

    event = _event("intake.item.received", workspace_id=None)
    await _aggregator(sm)(event)  # must not raise

    async with sm() as session:
        row = await session.scalar(
            select(AnalyticsEventRaw.id).where(
                AnalyticsEventRaw.source_event_id == uuid.UUID(event.id)
            )
        )
    assert row is None
