"""Evidence orchestration — corpus search → AI linking → persisted links.

Transactional shape: all evidence rows, all claim_evidence_links, the
contradiction review-flag update, and the EVIDENCE_COLLECTED outbox row
commit in ONE transaction (spec step 8).

Idempotency under at-least-once delivery: links already present at the
current LINKER_VERSION short-circuit re-delivery; the (claim_id,
evidence_id) primary key absorbs racing duplicates via ON CONFLICT
DO NOTHING. No ordering assumptions.

Degraded paths all converge on "claim proceeds with zero evidence":
zero candidates, exhausted AI budget, open circuit, and unparseable
linker output each emit EVIDENCE_COLLECTED with evidenceCount = 0 (the
last three also flag the claim for analyst review).
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.ai_circuit_breaker import CircuitOpenError
from oryx.core.logging import get_logger
from oryx.services.claims.repository import ClaimsRepository
from oryx.services.evidence.corpus_searcher import BM25Searcher
from oryx.services.evidence.events.constants import EVIDENCE_COLLECTED
from oryx.services.evidence.linker import LINKER_VERSION, EvidenceLinkerAI
from oryx.services.evidence.models import CandidateItem
from oryx.services.evidence.repository import EvidenceRepository
from oryx.services.queue.bus import DomainEvent
from oryx.services.queue.drainer import PermanentDeliveryError
from oryx.services.queue.outbox import enqueue_event
from oryx.services.verification.events.constants import AI_PARSE_FAILED

logger = get_logger(__name__)

SEARCH_STRATEGY = "bm25"


class EvidenceService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        linker: EvidenceLinkerAI | None = None,
        searcher_factory: Any = None,
    ) -> None:
        self._sm = sessionmaker
        self._linker = linker or EvidenceLinkerAI()
        # Injectable for tests; production builds a BM25Searcher per session.
        self._searcher_factory = searcher_factory or BM25Searcher

    async def collect_evidence_for_claim(
        self,
        *,
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[uuid.UUID]:
        """Returns the evidence ids linked to the claim afterwards."""
        # ---- Steps 1-3: load, guard, idempotency ----
        async with self._sm() as session:
            repo = EvidenceRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — evidence undeliverable"
                )
            claim = await repo.get_claim(workspace_id=workspace_id, claim_id=claim_id)
            if claim is None:
                raise PermanentDeliveryError(
                    f"claim {claim_id} not found — likely cascade-deleted"
                )
            claim_text = " ".join(
                part for part in (claim.subject, claim.predicate, claim.object) if part
            )
            subject = claim.subject
            predicate = claim.predicate
            exclude_item = claim.intake_item_id

            links = await repo.get_links_for_claim(claim_id)
            current = [l for l in links if l.linker_version == LINKER_VERSION]
            if current:
                # Idempotent re-delivery — links (and their event, written in
                # the same transaction) already exist.
                return [l.evidence_id for l in current]

            # ---- Step 4: corpus search ----
            searcher = self._searcher_factory(session)
            candidates: list[CandidateItem] = await searcher.search(
                workspace_id=workspace_id,
                subject=subject,
                predicate=predicate,
                exclude_intake_item_id=exclude_item,
            )

        # ---- Step 5: sparse corpus is a valid outcome ----
        if not candidates:
            await self._emit_collected(
                claim_id=claim_id,
                workspace_id=workspace_id,
                evidence_ids=[],
                causation_event_id=causation_event_id,
                correlation_id=correlation_id,
            )
            return []

        # ---- Budget gate (same pattern as Wave A) ----
        async with self._sm() as session:
            claims_repo = ClaimsRepository(session)
            if await claims_repo.budget_remaining(workspace_id) <= 0:
                logger.warning(
                    "evidence.budget_exceeded",
                    extra={"workspace_id": str(workspace_id), "stage": "linker"},
                )
                await claims_repo.flag_for_review(claim_id)
                await session.commit()
                await self._emit_collected(
                    claim_id=claim_id,
                    workspace_id=workspace_id,
                    evidence_ids=[],
                    causation_event_id=causation_event_id,
                    correlation_id=correlation_id,
                )
                return []

        # ---- Step 6: one batched AI call for all candidates ----
        try:
            linking = await self._linker.link(claim_text, candidates)
        except CircuitOpenError:
            logger.warning(
                "evidence.circuit_open",
                extra={"workspace_id": str(workspace_id), "stage": "linker"},
            )
            async with self._sm() as session:
                await ClaimsRepository(session).flag_for_review(claim_id)
                await session.commit()
            await self._emit_collected(
                claim_id=claim_id,
                workspace_id=workspace_id,
                evidence_ids=[],
                causation_event_id=causation_event_id,
                correlation_id=correlation_id,
            )
            return []

        # Spend is real even when the output is unusable — record it first.
        if linking.tokens_used:
            async with self._sm() as session:
                await ClaimsRepository(session).add_tokens_used(
                    workspace_id, linking.tokens_used
                )
                await session.commit()

        if linking.parse_failed:
            async with self._sm() as session:
                await ClaimsRepository(session).flag_for_review(claim_id)
                # Durable quality fact (2026-07-22 ADR): distinguishes "flagged
                # because the linker output was unparseable" from every other
                # review reason. Same transaction as the flag; analytics-only.
                await enqueue_event(
                    session,
                    name=AI_PARSE_FAILED,
                    payload={
                        "callType": "evidence_linker",
                        "workspaceId": str(workspace_id),
                        "claimId": str(claim_id),
                    },
                    workspace_id=workspace_id,
                    correlation_id=correlation_id,
                    causation_id=causation_event_id,
                )
                await session.commit()
            await self._emit_collected(
                claim_id=claim_id,
                workspace_id=workspace_id,
                evidence_ids=[],
                causation_event_id=causation_event_id,
                correlation_id=correlation_id,
            )
            return []

        included = [r for r in linking.results if r.include]
        excerpts = {c.intake_item_id: c.body_text_excerpt for c in candidates}

        # ---- Steps 7-9: ONE transaction for rows + links + flag + event ----
        evidence_ids: list[uuid.UUID] = []
        any_contradiction = False
        async with self._sm() as session:
            repo = EvidenceRepository(session)
            claims_repo = ClaimsRepository(session)
            for result in included:
                existing = await repo.find_evidence_for_item(
                    workspace_id=workspace_id, intake_item_id=result.intake_item_id
                )
                evidence = existing or await repo.insert_evidence(
                    workspace_id=workspace_id,
                    intake_item_id=result.intake_item_id,
                    evidence_type=result.evidence_type,
                    text=excerpts.get(result.intake_item_id, ""),
                )
                await repo.insert_link(
                    claim_id=claim_id,
                    evidence_id=evidence.id,
                    relationship=result.relationship,
                    strength=result.strength,
                    linker_version=LINKER_VERSION,
                )
                evidence_ids.append(evidence.id)
                if result.evidence_type == "contradiction":
                    any_contradiction = True

            if any_contradiction:
                # Same transaction as the inserts, per spec.
                await claims_repo.flag_for_review(claim_id)

            await enqueue_event(
                session,
                name=EVIDENCE_COLLECTED,
                payload=self._payload(claim_id, workspace_id, evidence_ids),
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                causation_id=causation_event_id,
            )
            await session.commit()
        return evidence_ids

    async def _emit_collected(
        self,
        *,
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        evidence_ids: list[uuid.UUID],
        causation_event_id: str | None,
        correlation_id: str | None,
    ) -> None:
        async with self._sm() as session:
            await enqueue_event(
                session,
                name=EVIDENCE_COLLECTED,
                payload=self._payload(claim_id, workspace_id, evidence_ids),
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                causation_id=causation_event_id,
            )
            await session.commit()

    @staticmethod
    def _payload(
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        evidence_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        return {
            "claimId": str(claim_id),
            "workspaceId": str(workspace_id),
            "evidenceIds": [str(e) for e in evidence_ids],
            "evidenceCount": len(evidence_ids),
            "searchStrategy": SEARCH_STRATEGY,
            "linkerVersion": LINKER_VERSION,
        }


class EvidenceCollectionHandler:
    """Subscriber for verification.claim.typed (registered in build_bus()).

    Idempotent via the (claim_id, LINKER_VERSION) link check in the
    service plus the (claim_id, evidence_id) primary key — the ADR-014
    §2.5 upsert-keyed variant used across the pipeline.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: EvidenceService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or EvidenceService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        claim_id = uuid.UUID(event.payload["claimId"])

        async with self._sm() as session:
            repo = EvidenceRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )

        await self._service.collect_evidence_for_claim(
            claim_id=claim_id,
            workspace_id=workspace_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
