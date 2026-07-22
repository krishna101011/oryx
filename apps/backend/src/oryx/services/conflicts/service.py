"""Conflict detection + resolution orchestration (Wave D).

Triggered by verification.claim.verified. For the just-verified claim we look
for same-subject, non-superseded, already-verified peers and decide whether
each pair conflicts:

  PATH A — an explicit 'contradicts' evidence link already ties the two
           claims' intake items: a deterministic conflict, no AI.
  PATH B — no such link but the predicates differ: ask the AI detector.

Each detected pair is inserted with canonical ordering (smaller UUID =
claim_a) under ON CONFLICT DO NOTHING, then either auto-resolved (all five
conditions in resolver.py) or escalated to an analyst — every state change
and its outbox event committed in ONE transaction.

Object-projection steps (recalculate an intelligence_object's score / set it
contested / emit OBJECT_UPDATED) are handled in Wave E by
ObjectConflictProjector, which subscribes to the CONFLICT_DETECTED /
CONFLICT_RESOLVED events emitted here — keeping conflict detection decoupled
from the intelligence domain (no import cycle).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.ai_circuit_breaker import CircuitOpenError
from oryx.core.logging import get_logger
from oryx.core.models import Claim
from oryx.services.claims.repository import ClaimsRepository
from oryx.services.conflicts.detector import ConflictDetectorAI
from oryx.services.conflicts.events.constants import (
    CONFLICT_DETECTED,
    CONFLICT_RESOLVED,
)
from oryx.services.conflicts.repository import ConflictRepository
from oryx.services.conflicts.resolver import evaluate_auto_resolve
from oryx.services.queue.bus import DomainEvent
from oryx.services.queue.drainer import PermanentDeliveryError
from oryx.services.queue.outbox import enqueue_event
from oryx.services.verification.events.constants import AI_PARSE_FAILED

logger = get_logger(__name__)


@dataclass(frozen=True)
class _ClaimInfo:
    id: uuid.UUID
    subject: str
    predicate: str
    object: str | None
    item_id: uuid.UUID
    confidence: float | None
    source_accuracy: float
    requires_review: bool


@dataclass(frozen=True)
class _PlannedConflict:
    candidate: _ClaimInfo
    conflict_type: str
    severity: float


class ConflictService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        detector: ConflictDetectorAI | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._detector = detector or ConflictDetectorAI()

    async def detect_for_claim(
        self,
        *,
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        # ---- Read phase: snapshot the claim, its peers, and their facts ----
        async with self._sm() as session:
            repo = ConflictRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — conflicts undeliverable"
                )
            current = await repo.get_claim(
                workspace_id=workspace_id, claim_id=claim_id
            )
            if current is None or current.superseded_by is not None:
                # Cascade-deleted or already superseded — nothing to detect.
                return

            current_info = await self._load_info(repo, workspace_id, current)
            candidates = await repo.find_candidate_claims(
                workspace_id=workspace_id,
                subject=current.subject,
                exclude_claim_id=claim_id,
            )
            already_paired = await repo.existing_conflict_partner_ids(
                workspace_id=workspace_id, claim_id=claim_id
            )

            planned: list[_PlannedConflict] = []
            ai_candidates: list[_ClaimInfo] = []
            for cand in candidates:
                if cand.id in already_paired:
                    continue  # pair already recorded — idempotent skip, no AI
                cand_info = await self._load_info(repo, workspace_id, cand)
                strength = await repo.contradiction_link_strength(
                    claim_a_id=current.id,
                    claim_a_item_id=current_info.item_id,
                    claim_b_id=cand.id,
                    claim_b_item_id=cand_info.item_id,
                )
                if strength is not None:
                    # PATH A — deterministic, no AI.
                    planned.append(
                        _PlannedConflict(
                            candidate=cand_info,
                            conflict_type="direct_contradiction",
                            severity=strength,
                        )
                    )
                elif current.predicate != cand_info.predicate:
                    ai_candidates.append(cand_info)  # PATH B — needs AI

        # ---- PATH B AI calls (outside any transaction) ----
        for cand_info in ai_candidates:
            planned_b = await self._detect_with_ai(
                workspace_id=workspace_id, a=current_info, b=cand_info
            )
            if planned_b is not None:
                planned.append(planned_b)

        # ---- Write phase: one transaction per conflict ----
        for plan in planned:
            await self._record_conflict(
                workspace_id=workspace_id,
                current=current_info,
                plan=plan,
                causation_event_id=causation_event_id,
                correlation_id=correlation_id,
            )

    async def _load_info(
        self, repo: ConflictRepository, workspace_id: uuid.UUID, claim: Claim
    ) -> _ClaimInfo:
        item = await repo.get_intake_item(claim.intake_item_id)
        if item is None:
            raise PermanentDeliveryError(
                f"intake item {claim.intake_item_id} missing — cascade-deleted"
            )
        accuracy = await repo.get_source_accuracy(
            workspace_id=workspace_id, source_id=item.intake_source_id
        )
        confidence = await repo.latest_confidence(claim.id)
        return _ClaimInfo(
            id=claim.id,
            subject=claim.subject,
            predicate=claim.predicate,
            object=claim.object,
            item_id=claim.intake_item_id,
            confidence=confidence,
            source_accuracy=accuracy,
            requires_review=claim.requires_analyst_review,
        )

    async def _detect_with_ai(
        self, *, workspace_id: uuid.UUID, a: _ClaimInfo, b: _ClaimInfo
    ) -> _PlannedConflict | None:
        # Budget gate — same ledger the claim/evidence services use.
        async with self._sm() as session:
            if await ClaimsRepository(session).budget_remaining(workspace_id) <= 0:
                logger.warning(
                    "conflicts.budget_exceeded",
                    extra={"workspace_id": str(workspace_id)},
                )
                return None

        try:
            detection = await self._detector.detect(
                subject=a.subject,
                a_predicate=a.predicate,
                a_object=a.object,
                b_predicate=b.predicate,
                b_object=b.object,
            )
        except CircuitOpenError:
            logger.warning(
                "conflicts.circuit_open",
                extra={"workspace_id": str(workspace_id)},
            )
            return None

        if detection.tokens_used or detection.parse_failed:
            async with self._sm() as session:
                if detection.tokens_used:
                    await ClaimsRepository(session).add_tokens_used(
                        workspace_id, detection.tokens_used
                    )
                if detection.parse_failed:
                    # Durable quality fact (2026-07-22 ADR): without this, an
                    # unparseable detector response is byte-for-byte identical
                    # to a genuine "no conflict" downstream. Analytics-only.
                    await enqueue_event(
                        session,
                        name=AI_PARSE_FAILED,
                        payload={
                            "callType": "conflict_detector",
                            "workspaceId": str(workspace_id),
                            "claimAId": str(a.id),
                            "claimBId": str(b.id),
                        },
                        workspace_id=workspace_id,
                    )
                await session.commit()

        if not detection.result.is_conflict:
            return None
        return _PlannedConflict(
            candidate=b,
            conflict_type=detection.result.conflict_type,
            severity=detection.result.severity,
        )

    async def _record_conflict(
        self,
        *,
        workspace_id: uuid.UUID,
        current: _ClaimInfo,
        plan: _PlannedConflict,
        causation_event_id: str | None,
        correlation_id: str | None,
    ) -> None:
        cand = plan.candidate
        # Canonical ordering: smaller UUID is always claim_a.
        if current.id <= cand.id:
            a_info, b_info = current, cand
        else:
            a_info, b_info = cand, current

        async with self._sm() as session:
            repo = ConflictRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted mid-detection"
                )
            conflict = await repo.insert_conflict(
                workspace_id=workspace_id,
                claim_a_id=a_info.id,
                claim_b_id=b_info.id,
                conflict_type=plan.conflict_type,
                severity=plan.severity,
            )
            if conflict is None:
                return  # pair already recorded — idempotent re-delivery

            decision = evaluate_auto_resolve(
                severity=plan.severity,
                conflict_type=plan.conflict_type,
                score_a=a_info.confidence,
                score_b=b_info.confidence,
                a_requires_review=a_info.requires_review,
                b_requires_review=b_info.requires_review,
                a_source_accuracy=a_info.source_accuracy,
                b_source_accuracy=b_info.source_accuracy,
            )

            if decision.auto_resolve:
                winner_id = a_info.id if decision.winner_is_a else b_info.id
                loser_id = b_info.id if decision.winner_is_a else a_info.id
                note = (
                    f"System auto-resolved: claim {winner_id} wins "
                    f"(severity={plan.severity:.3f}, "
                    f"score_ratio={decision.score_ratio}, "
                    f"type={plan.conflict_type}, "
                    f"scores a={a_info.confidence} b={b_info.confidence}, "
                    f"requires_review a={a_info.requires_review} "
                    f"b={b_info.requires_review}, "
                    f"source_accuracy a={a_info.source_accuracy} "
                    f"b={b_info.source_accuracy})."
                )
                await repo.resolve_conflict_system(
                    conflict_id=conflict.id,
                    winner_id=winner_id,
                    loser_id=loser_id,
                    note=note,
                )
                await repo.write_audit(
                    workspace_id=workspace_id,
                    account_id=None,
                    event="conflict_resolved",
                    entity_type="conflict",
                    entity_id=conflict.id,
                    data={
                        "resolution": "system",
                        "winner_id": str(winner_id),
                        "loser_id": str(loser_id),
                        "severity": plan.severity,
                        "score_ratio": decision.score_ratio,
                        "conflict_type": plan.conflict_type,
                        "requires_analyst_review_flags": {
                            "a": a_info.requires_review,
                            "b": b_info.requires_review,
                        },
                        "source_accuracy_rates": {
                            "a": a_info.source_accuracy,
                            "b": b_info.source_accuracy,
                        },
                        "conditions": decision.conditions,
                    },
                )
                # Object projection (Wave E): ObjectConflictProjector consumes
                # this CONFLICT_RESOLVED event and recomposes the affected
                # object — score recalculated without the superseded claim,
                # status restored when no open conflicts remain — emitting
                # OBJECT_UPDATED(changeType='conflict_resolved').
                await enqueue_event(
                    session,
                    name=CONFLICT_RESOLVED,
                    payload={
                        "conflictId": str(conflict.id),
                        "claimAId": str(a_info.id),
                        "claimBId": str(b_info.id),
                        "resolution": "system",
                        "winnerId": str(winner_id),
                        "loserId": str(loser_id),
                        "status": "resolved_system",
                        "workspaceId": str(workspace_id),
                    },
                    workspace_id=workspace_id,
                    correlation_id=correlation_id,
                    causation_id=causation_event_id,
                )
            else:
                await repo.set_requires_review(a_info.id, True)
                await repo.set_requires_review(b_info.id, True)
                await repo.write_audit(
                    workspace_id=workspace_id,
                    account_id=None,
                    event="conflict_detected",
                    entity_type="conflict",
                    entity_id=conflict.id,
                    data={
                        "resolution": "escalated",
                        "severity": plan.severity,
                        "conflict_type": plan.conflict_type,
                        "score_a": a_info.confidence,
                        "score_b": b_info.confidence,
                        "conditions": decision.conditions,
                    },
                )
                # Object projection (Wave E): ObjectConflictProjector consumes
                # this CONFLICT_DETECTED event and recomposes the affected
                # object(s), which moves verification_status to 'contested',
                # emitting OBJECT_UPDATED(changeType='conflict_detected').
                await enqueue_event(
                    session,
                    name=CONFLICT_DETECTED,
                    payload={
                        "conflictId": str(conflict.id),
                        "claimAId": str(a_info.id),
                        "claimBId": str(b_info.id),
                        "conflictType": plan.conflict_type,
                        "severity": plan.severity,
                        "status": "open",
                        "workspaceId": str(workspace_id),
                    },
                    workspace_id=workspace_id,
                    correlation_id=correlation_id,
                    causation_id=causation_event_id,
                )
            await session.commit()


class ConflictDetectionHandler:
    """Subscriber for verification.claim.verified (registered in build_bus()).

    Idempotent via the ON CONFLICT DO NOTHING pair guard plus the
    already-paired pre-filter. No ordering assumptions.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: ConflictService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or ConflictService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        claim_id = uuid.UUID(event.payload["claimId"])

        async with self._sm() as session:
            repo = ConflictRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )

        await self._service.detect_for_claim(
            claim_id=claim_id,
            workspace_id=workspace_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
