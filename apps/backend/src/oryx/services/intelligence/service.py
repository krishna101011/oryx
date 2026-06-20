"""Intelligence orchestration (Wave E).

CompositionTriggerHandler (on verification.claim.verified) is the fan-in: once
EVERY claim for an intake item is terminal, it composes the one intelligence
object for that item — once. It never auto-recomposes on a scoring_version bump
(stale detection is a read-only API concern); an existing object short-circuits.

ObjectConflictProjector (on verification.conflict.detected / .resolved) is the
Wave D seam fill: a conflict that fires for a claim recomposes the object(s)
containing that claim, which moves status to contested (detected) or back to
verified/unverified (resolved, after supersession), preserving sticky analyst
statuses. It emits OBJECT_UPDATED, plus OBJECT_REVIEWED when an analyst drove
the resolution.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import Claim
from oryx.services.conflicts.events.constants import (
    CONFLICT_DETECTED,
    CONFLICT_RESOLVED,
)
from oryx.services.intelligence.composer import ObjectComposer
from oryx.services.intelligence.events.constants import (
    OBJECT_CREATED,
    OBJECT_REVIEWED,
    OBJECT_UPDATED,
)
from oryx.services.intelligence.repository import (
    STICKY_STATUSES,
    IntelligenceRepository,
)
from oryx.services.queue.bus import DomainEvent
from oryx.services.queue.drainer import PermanentDeliveryError
from oryx.services.queue.outbox import enqueue_event

logger = get_logger(__name__)


class IntelligenceService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        composer: ObjectComposer | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._composer = composer or ObjectComposer()

    async def compose_for_item(
        self,
        *,
        intake_item_id: uuid.UUID,
        workspace_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> uuid.UUID | None:
        async with self._sm() as session:
            repo = IntelligenceRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — composition undeliverable"
                )

            claims = await repo.all_claims_for_item(
                workspace_id=workspace_id, intake_item_id=intake_item_id
            )
            if not claims:
                return None  # nothing to compose

            # Fan-in gate: ALL claims must be terminal before composing.
            terminal = await repo.terminal_claim_ids([c.id for c in claims])
            if len(terminal) < len(claims):
                return None  # a non-terminal claim blocks composition

            # Idempotency + no auto-recalc on version bump: an existing object
            # (any scoring_version) short-circuits.
            existing = await repo.get_object_by_item(
                workspace_id=workspace_id, intake_item_id=intake_item_id
            )
            if existing is not None:
                return existing.id

            result = await self._composer.compose(
                intake_item_id=intake_item_id,
                workspace_id=workspace_id,
                session=session,
            )
            obj = await repo.insert_object(
                workspace_id=workspace_id,
                intake_item_id=intake_item_id,
                result=result,
            )
            if obj is None:
                return None  # lost the insert race — the winner composed it

            await repo.write_audit(
                workspace_id=workspace_id,
                account_id=None,
                event="object_created",
                entity_id=obj.id,
                data={
                    "intake_item_id": str(intake_item_id),
                    "epistemic_type": result.epistemic_type,
                    "verification_status": result.verification_status,
                    "confidence_score": result.confidence_score,
                    "claim_count": len(result.claim_ids),
                },
            )
            await enqueue_event(
                session,
                name=OBJECT_CREATED,
                payload={
                    "objectId": str(obj.id),
                    "workspaceId": str(workspace_id),
                    "intakeItemId": str(intake_item_id),
                    "epistemicType": result.epistemic_type,
                    "verificationStatus": result.verification_status,
                    "confidenceScore": result.confidence_score,
                },
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                causation_id=causation_event_id,
            )
            await session.commit()
            return obj.id

    async def recompose_for_conflict(
        self,
        *,
        claim_a_id: uuid.UUID,
        claim_b_id: uuid.UUID,
        workspace_id: uuid.UUID,
        change_type: str,
        resolution: str | None,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        async with self._sm() as session:
            repo = IntelligenceRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )

            item_ids: set[uuid.UUID] = set()
            for cid in (claim_a_id, claim_b_id):
                claim = await session.get(Claim, cid)
                if claim is not None and claim.workspace_id == workspace_id:
                    item_ids.add(claim.intake_item_id)

            for item_id in item_ids:
                obj = await repo.get_object_by_item(
                    workspace_id=workspace_id, intake_item_id=item_id
                )
                if obj is None:
                    continue  # no object composed for this item yet
                result = await self._composer.compose(
                    intake_item_id=item_id,
                    workspace_id=workspace_id,
                    session=session,
                )
                # Sticky analyst status: a recompose never overwrites an
                # analyst_approved / analyst_rejected verdict.
                final_status = (
                    obj.verification_status
                    if obj.verification_status in STICKY_STATUSES
                    else result.verification_status
                )
                await repo.apply_composition(
                    object_id=obj.id, result=result, status=final_status
                )
                await enqueue_event(
                    session,
                    name=OBJECT_UPDATED,
                    payload={
                        "objectId": str(obj.id),
                        "workspaceId": str(workspace_id),
                        "changeType": change_type,
                    },
                    workspace_id=workspace_id,
                    correlation_id=correlation_id,
                    causation_id=causation_event_id,
                )
                if resolution == "analyst":
                    await enqueue_event(
                        session,
                        name=OBJECT_REVIEWED,
                        payload={
                            "objectId": str(obj.id),
                            "workspaceId": str(workspace_id),
                            "reviewOutcome": "conflict_resolved",
                        },
                        workspace_id=workspace_id,
                        correlation_id=correlation_id,
                        causation_id=causation_event_id,
                    )
            await session.commit()


class CompositionTriggerHandler:
    """Subscriber for verification.claim.verified (registered in build_bus()).

    Loads the claim to find its intake item, then composes. Idempotent via the
    one-object-per-item guard; no ordering assumptions. Coexists with
    ConflictDetectionHandler on the same event.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: IntelligenceService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or IntelligenceService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        claim_id = uuid.UUID(event.payload["claimId"])

        async with self._sm() as session:
            repo = IntelligenceRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )
            claim = await session.get(Claim, claim_id)
            if claim is None:
                return  # cascade-deleted; nothing to compose
            intake_item_id = claim.intake_item_id

        await self._service.compose_for_item(
            intake_item_id=intake_item_id,
            workspace_id=workspace_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )


class ObjectConflictProjector:
    """Subscriber for verification.conflict.detected / .resolved.

    Fills the Wave D object-projection seams: recompose the affected object(s)
    so a detected conflict marks them contested and a resolution restores them.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: IntelligenceService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or IntelligenceService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        claim_a_id = uuid.UUID(event.payload["claimAId"])
        claim_b_id = uuid.UUID(event.payload["claimBId"])

        if event.name == CONFLICT_DETECTED:
            change_type = "conflict_detected"
            resolution: str | None = None
        elif event.name == CONFLICT_RESOLVED:
            change_type = "conflict_resolved"
            resolution = event.payload.get("resolution")
        else:  # defensive — not subscribed to anything else
            return

        await self._service.recompose_for_conflict(
            claim_a_id=claim_a_id,
            claim_b_id=claim_b_id,
            workspace_id=workspace_id,
            change_type=change_type,
            resolution=resolution,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
