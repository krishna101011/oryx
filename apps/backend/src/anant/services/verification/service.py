"""Verification orchestration — evidence-linked claim -> outcome + score.

Per §16.1 STEP 4: load the claim, its evidence links, and the source's
current credibility; run the deterministic engine and scorer (no AI); then
— in ONE transaction — write the verification_run, update source credibility,
write the verification_audit_log entry, and enqueue CLAIM_VERIFIED.

Idempotency under at-least-once delivery: a completed run at the current
(engine_version, scoring_version) short-circuits re-delivery; because the
run and its CLAIM_VERIFIED outbox row commit together, returning early is
safe. No ordering assumptions.

The whole step is AI-free, so there is no budget or circuit-breaker gate
here — verification is pure arithmetic over data Waves A-B already produced.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from anant.core.logging import get_logger
from anant.core.models import VerificationRun
from anant.services.queue.bus import DomainEvent
from anant.services.queue.drainer import PermanentDeliveryError
from anant.services.queue.outbox import enqueue_event
from anant.services.verification.credibility import next_accuracy
from anant.services.verification.engine import ENGINE_VERSION, VerificationEngine
from anant.services.verification.events.constants import CLAIM_VERIFIED
from anant.services.verification.repository import VerificationRepository
from anant.services.verification.scorer import SCORING_VERSION, ConfidenceScorer

logger = get_logger(__name__)


class VerificationService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        engine: VerificationEngine | None = None,
        scorer: ConfidenceScorer | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._engine = engine or VerificationEngine()
        self._scorer = scorer or ConfidenceScorer()

    async def verify_claim(
        self,
        *,
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> uuid.UUID | None:
        """Run verification for one claim. Returns the run id (or the existing
        run's id on idempotent re-delivery)."""
        async with self._sm() as session:
            repo = VerificationRepository(session)

            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — verification undeliverable"
                )
            claim = await repo.get_claim(workspace_id=workspace_id, claim_id=claim_id)
            if claim is None:
                raise PermanentDeliveryError(
                    f"claim {claim_id} not found — likely cascade-deleted"
                )

            # Idempotency: a complete run at the current versions already
            # emitted CLAIM_VERIFIED in its own transaction.
            existing = await repo.latest_complete_run(
                claim_id=claim_id,
                engine_version=ENGINE_VERSION,
                scoring_version=SCORING_VERSION,
            )
            if existing is not None:
                return existing.id

            intake_item = await repo.get_intake_item(claim.intake_item_id)
            if intake_item is None:
                # The item (and normally the claim, via FK cascade) is gone.
                raise PermanentDeliveryError(
                    f"intake item {claim.intake_item_id} missing — cascade-deleted"
                )
            source_id = intake_item.intake_source_id

            accuracy = await repo.get_accuracy(
                workspace_id=workspace_id, source_id=source_id
            )
            links = await repo.get_evidence_links(claim_id)
            now = datetime.now(UTC)

            outcome = self._engine.determine_outcome(claim.epistemic_type, links)
            scoring = self._scorer.score(
                epistemic_type=claim.epistemic_type,
                accuracy_rate=accuracy,
                links=links,
                received_at=intake_item.received_at,
                object_text=claim.object,
                now=now,
            )
            f = scoring.factors

            run = await repo.insert_run(
                VerificationRun(
                    id=uuid.uuid4(),
                    claim_id=claim_id,
                    status="complete",
                    outcome=outcome,
                    source_trust_score=f.source_trust_score,
                    cross_reference_count=f.cross_reference_count,
                    evidence_strength=f.evidence_strength_score,
                    recency_score=f.recency_score,
                    claim_specificity=f.claim_specificity_score,
                    primary_source_flag=f.primary_source_flag,
                    confidence_score=scoring.confidence_score,
                    factors=f.as_dict(),
                    engine_version=ENGINE_VERSION,
                    scoring_version=SCORING_VERSION,
                    started_at=now,
                    completed_at=now,
                )
            )

            # Credibility feedback — same transaction (acceptance criterion).
            # Scored with the pre-run accuracy; now nudge it by this outcome.
            await repo.apply_credibility_outcome(
                workspace_id=workspace_id,
                source_id=source_id,
                outcome=outcome,
                new_accuracy=next_accuracy(accuracy, outcome),
            )

            await repo.write_audit(
                workspace_id=workspace_id,
                account_id=None,
                event="verification_complete",
                entity_type="claim",
                entity_id=claim_id,
                data={
                    "verification_run_id": str(run.id),
                    "outcome": outcome,
                    "confidence_score": scoring.confidence_score,
                    "source_id": str(source_id),
                },
            )

            await enqueue_event(
                session,
                name=CLAIM_VERIFIED,
                payload={
                    "claimId": str(claim_id),
                    "verificationRunId": str(run.id),
                    "outcome": outcome,
                    "confidenceScore": scoring.confidence_score,
                    "engineVersion": ENGINE_VERSION,
                    "scoringVersion": SCORING_VERSION,
                    "workspaceId": str(workspace_id),
                },
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                causation_id=causation_event_id,
            )
            await session.commit()
            return run.id


class VerificationHandler:
    """Subscriber for verification.evidence.collected (registered in build_bus()).

    Idempotent via the service's complete-run check (claim_id + engine +
    scoring version). No ordering or exactly-once assumptions.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: VerificationService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or VerificationService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        claim_id = uuid.UUID(event.payload["claimId"])

        async with self._sm() as session:
            repo = VerificationRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )

        await self._service.verify_claim(
            claim_id=claim_id,
            workspace_id=workspace_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
