"""Claims orchestration — extraction fan-out + epistemic typing.

Transactional shape (the Wave A contract):

  Phase 1 (ATOMIC): all claim inserts for one intake item and their
  CLAIM_EXTRACTED outbox rows commit together or not at all. Partial
  fan-out cannot exist.

  Phase 2 (per claim): classify → update epistemic_type + CLAIM_TYPED
  outbox row in one transaction per claim.

Idempotency (at-least-once delivery, ADR-014 §2.5 upsert variant —
the same pattern Phase 3 uses for intake items):
  - The (workspace_id, intake_item_id, text) unique constraint makes a
    duplicate extraction a silent no-op.
  - A re-delivered event with claims already at the current
    EXTRACTOR_VERSION skips extraction entirely — but still RESUMES
    classification for any claim left unclassified by a crash between
    Phase 1 and Phase 2 (without this, those claims stay untyped forever).

Budget policy (workspace_ai_budget, checked BEFORE every AI call):
  - Exhausted before extraction → nothing exists to flag for review, so
    the delivery is deferred: structured `claims.budget_exceeded` log +
    transient raise (drainer backoff; ledger resets daily).
  - Exhausted before a classification → the claim stays 'unclassified'
    with requires_analyst_review=true (analyst takes over, per spec);
    no CLAIM_TYPED is emitted because no typing happened.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from anant.core.ai_circuit_breaker import CircuitOpenError
from anant.core.logging import get_logger
from anant.services.claims.classifier import CLASSIFIER_VERSION, EpistemicClassifierAI
from anant.services.claims.events.constants import CLAIM_EXTRACTED, CLAIM_TYPED
from anant.services.claims.extractor import EXTRACTOR_VERSION, ClaimExtractorAI
from anant.services.claims.repository import ClaimsRepository
from anant.services.queue.bus import DomainEvent
from anant.services.queue.drainer import PermanentDeliveryError
from anant.services.queue.outbox import enqueue_event

logger = get_logger(__name__)


class NormalizedRowMissingError(Exception):
    """Intake normalization hasn't landed yet — valid timing case.

    Deliberately NOT a PermanentDeliveryError: the drainer retries with
    backoff and the row appears once intake's transaction is visible.
    """


class BudgetExhaustedError(Exception):
    """Daily AI budget spent before extraction could run — defer delivery."""


class ClaimService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        extractor: ClaimExtractorAI | None = None,
        classifier: EpistemicClassifierAI | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._extractor = extractor or ClaimExtractorAI()
        self._classifier = classifier or EpistemicClassifierAI()

    async def extract_claims_from_intake_item(
        self,
        *,
        intake_item_id: uuid.UUID,
        workspace_id: uuid.UUID,
        causation_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[uuid.UUID]:
        """Run both pipeline steps for one intake item.

        Returns the ids of every claim that exists for the item afterwards
        (inserted now or already present).
        """
        # ---- Step 1: load the normalized row (may not exist yet) ----
        async with self._sm() as session:
            repo = ClaimsRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — claims undeliverable"
                )
            normalized = await repo.get_normalized_item(intake_item_id)
            if normalized is None:
                raise NormalizedRowMissingError(
                    f"no normalized row yet for intake item {intake_item_id}"
                )
            body_text = normalized.body_text or ""
            context = body_text[:500]

            # ---- Step 2: idempotency / version check ----
            existing = await repo.get_claims_for_item(
                workspace_id=workspace_id, intake_item_id=intake_item_id
            )
            current_version_rows = [
                c for c in existing if c.extractor_version == EXTRACTOR_VERSION
            ]

        if current_version_rows:
            # Idempotent re-delivery: no re-extraction. But finish typing
            # anything a crash left unclassified. The original CLAIM_EXTRACTED
            # event ids are unknown here (those rows may already be pruned),
            # so causation falls back to the re-delivered intake event.
            pending = {
                c.id: causation_event_id
                for c in current_version_rows
                if c.classifier_version is None
            }
            if pending:
                await self._classify_claims(
                    workspace_id=workspace_id,
                    claim_causations=pending,
                    context=context,
                    correlation_id=correlation_id,
                )
            return [c.id for c in current_version_rows]

        # An item with no text asserts nothing — don't spend AI budget
        # discovering that.
        if not body_text.strip():
            return []

        # ---- Step 3: extract (budget-gated) ----
        # Known bound (flagged for the Wave C verification_runs ledger): the
        # check below and the spend recorded after the call are not one
        # atomic unit, so a crash-then-redelivery can run one extraction
        # past an already-exhausted budget. The overrun is bounded to a
        # single item's calls and self-corrects — spend accumulates via the
        # ON CONFLICT upsert, so the next check blocks.
        async with self._sm() as session:
            repo = ClaimsRepository(session)
            if await repo.budget_remaining(workspace_id) <= 0:
                # No verification_audit_log table exists in Wave A — the
                # exceeded signal goes to structured logs (flagged in the
                # wave report for architecture review).
                logger.warning(
                    "claims.budget_exceeded",
                    extra={"workspace_id": str(workspace_id), "stage": "extractor"},
                )
                raise BudgetExhaustedError(
                    f"AI budget exhausted for workspace {workspace_id}"
                )

        extraction = await self._extractor.extract(body_text)

        # Record spend immediately and durably — even if the fan-out below
        # fails, the tokens were really consumed.
        if extraction.tokens_used:
            async with self._sm() as session:
                await ClaimsRepository(session).add_tokens_used(
                    workspace_id, extraction.tokens_used
                )
                await session.commit()

        if extraction.parse_failed:
            logger.warning(
                "claims.extraction_unparseable",
                extra={
                    "workspace_id": str(workspace_id),
                    "intake_item_id": str(intake_item_id),
                },
            )
            return []
        if not extraction.triples:
            return []  # zero claims is a valid outcome

        # ---- Steps 4-5: atomic fan-out (claims + CLAIM_EXTRACTED rows) ----
        # claim id → its CLAIM_EXTRACTED event id (the causation parent of
        # the CLAIM_TYPED that follows).
        extracted_events: dict[uuid.UUID, str] = {}
        try:
            async with self._sm() as session:
                repo = ClaimsRepository(session)
                if not await repo.workspace_exists(workspace_id):
                    raise PermanentDeliveryError(
                        f"workspace {workspace_id} deleted mid-extraction"
                    )
                for triple in extraction.triples:
                    claim_id = await repo.insert_claim(
                        workspace_id=workspace_id,
                        intake_item_id=intake_item_id,
                        text=triple.text,
                        subject=triple.subject,
                        predicate=triple.predicate,
                        object_=triple.object,
                        extractor_version=EXTRACTOR_VERSION,
                    )
                    if claim_id is None:
                        continue  # idempotency guard: same text already extracted
                    event_id = await enqueue_event(
                        session,
                        name=CLAIM_EXTRACTED,
                        payload={
                            "claimId": str(claim_id),
                            "intakeItemId": str(intake_item_id),
                            "workspaceId": str(workspace_id),
                            "epistemicTypeHint": "unclassified",
                            "extractorVersion": EXTRACTOR_VERSION,
                        },
                        workspace_id=workspace_id,
                        correlation_id=correlation_id,
                        causation_id=causation_event_id,
                    )
                    extracted_events[claim_id] = str(event_id)
                await session.commit()
        except IntegrityError as e:
            # TOCTOU with the CR-6 cascade: the workspace (and its items)
            # can be hard-deleted between the existence check and the
            # inserts. The transaction rolled back atomically; decide
            # terminal vs transient from the current workspace state.
            async with self._sm() as session:
                if not await ClaimsRepository(session).workspace_exists(workspace_id):
                    raise PermanentDeliveryError(
                        f"workspace {workspace_id} deleted during fan-out"
                    ) from e
            raise  # some other integrity problem — let the drainer retry

        # ---- Step 6: epistemic typing, one transaction per claim ----
        await self._classify_claims(
            workspace_id=workspace_id,
            claim_causations=extracted_events,
            context=context,
            correlation_id=correlation_id,
        )
        return list(extracted_events.keys())

    async def _classify_claims(
        self,
        *,
        workspace_id: uuid.UUID,
        claim_causations: Mapping[uuid.UUID, str | None],
        context: str,
        correlation_id: str | None,
    ) -> None:
        """`claim_causations` maps each claim id to the event id that caused
        its typing — the claim's CLAIM_EXTRACTED event on the normal path,
        or the re-delivered intake event on the resume path."""
        for claim_id, causation_event_id in claim_causations.items():
            async with self._sm() as session:
                repo = ClaimsRepository(session)
                claim = await repo.get_claim(
                    workspace_id=workspace_id, claim_id=claim_id
                )
                if claim is None:  # cascade-deleted underneath us
                    continue
                claim_text = claim.text

                if await repo.budget_remaining(workspace_id) <= 0:
                    logger.warning(
                        "claims.budget_exceeded",
                        extra={"workspace_id": str(workspace_id), "stage": "classifier"},
                    )
                    # Claim stays 'unclassified' / classifier_version NULL;
                    # the analyst takes over. No CLAIM_TYPED — nothing was typed.
                    await repo.flag_for_review(claim_id)
                    await session.commit()
                    continue

            try:
                result = await self._classifier.classify(claim_text, context)
            except CircuitOpenError:
                # Wave B §21.2: circuit open → flag for analyst, leave the
                # claim unclassified (same terminal shape as budget-skip;
                # no CLAIM_TYPED because nothing was typed).
                logger.warning(
                    "claims.circuit_open",
                    extra={"workspace_id": str(workspace_id), "stage": "classifier"},
                )
                async with self._sm() as session:
                    await ClaimsRepository(session).flag_for_review(claim_id)
                    await session.commit()
                continue

            async with self._sm() as session:
                repo = ClaimsRepository(session)
                if result.tokens_used:
                    await repo.add_tokens_used(workspace_id, result.tokens_used)
                await repo.set_epistemic_type(
                    claim_id=claim_id,
                    epistemic_type=result.epistemic_type,
                    classifier_version=CLASSIFIER_VERSION,
                    requires_analyst_review=result.requires_analyst_review,
                )
                await enqueue_event(
                    session,
                    name=CLAIM_TYPED,
                    payload={
                        "claimId": str(claim_id),
                        "epistemicType": result.epistemic_type,
                        "classifierVersion": CLASSIFIER_VERSION,
                        "workspaceId": str(workspace_id),
                        "requiresAnalystReview": result.requires_analyst_review,
                    },
                    workspace_id=workspace_id,
                    correlation_id=correlation_id,
                    causation_id=causation_event_id,
                )
                await session.commit()


class ClaimExtractionHandler:
    """Subscriber for intake.item.received (registered in build_bus()).

    Idempotent under at-least-once delivery via the domain guard
    (unique claim constraint + extractor-version check) — the ADR-014
    §2.5 "upsert keyed on the payload identifier" variant that Phase 3
    established. No event ordering is assumed.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        service: ClaimService | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._service = service or ClaimService(sessionmaker)

    async def __call__(self, event: DomainEvent) -> None:
        workspace_id = uuid.UUID(event.payload["workspaceId"])
        intake_item_id = uuid.UUID(event.payload["intakeItemId"])

        async with self._sm() as session:
            repo = ClaimsRepository(session)
            if not await repo.workspace_exists(workspace_id):
                raise PermanentDeliveryError(
                    f"workspace {workspace_id} deleted — dead-lettering"
                )

        await self._service.extract_claims_from_intake_item(
            intake_item_id=intake_item_id,
            workspace_id=workspace_id,
            causation_event_id=event.id,
            correlation_id=event.correlation_id,
        )
