"""Claim pipeline end-to-end against Postgres (Phase 4 Wave A).

Fake AI components are injected through the ClaimService seams — the full
DB path (idempotency guard, atomic fan-out, budget ledger, outbox rows,
causation chain) runs against real tables with zero network.
Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update

pytestmark = pytest.mark.requires_db


async def _seed_item(sm) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Workspace + source + one ingested item (with normalized row).

    Returns (workspace_id, intake_item_id, intake_event_id)."""
    from anant.core.models import Account, IntakeSource, OutboxEvent, Workspace
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"claims+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Claims WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()
        ingest = await IntakeService(session).ingest_raw_item(
            workspace_id=workspace.id,
            intake_source_id=source.id,
            provider_name="rss",
            raw=RawItem(
                external_id=f"art-{uuid.uuid4().hex[:8]}",
                received_at=datetime.now(UTC),
                sender="Example Wire",
                subject="Apple results",
                body_text="Apple Inc reported revenue of $94.9 billion in Q1.",
                body_html=None,
                links=[],
                payload={},
            ),
        )
        await session.commit()
        item_id = ingest.intake_item_id
        assert item_id is not None
        row = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == workspace.id,
                )
            )
        ).scalars().one()
        return workspace.id, item_id, str(row.id)


class FakeExtractor:
    """Deterministic stand-in honoring the ExtractionResult contract."""

    version = 1

    def __init__(self, triples=None, tokens: int = 120, fail_if_called: bool = False):
        from anant.services.claims.models import ClaimTriple

        self._fail = fail_if_called
        self.calls = 0
        self.tokens = tokens
        self.triples = (
            triples
            if triples is not None
            else [
                ClaimTriple(
                    subject="Apple Inc",
                    predicate="reported revenue of",
                    object="$94.9 billion",
                    text="Apple Inc reported revenue of $94.9 billion in Q1.",
                ),
                ClaimTriple(
                    subject="Apple Inc",
                    predicate="guided margins to",
                    object="46%",
                    text="Apple Inc guided margins to 46% for Q2.",
                ),
            ]
        )

    async def extract(self, body_text: str):
        from anant.services.claims.extractor import ExtractionResult

        if self._fail:
            raise AssertionError("extractor must not be called on this path")
        self.calls += 1
        return ExtractionResult(
            triples=self.triples, tokens_used=self.tokens, parse_failed=False
        )


class FakeClassifier:
    version = 1

    def __init__(self, label: str = "claim"):
        self.label = label
        self.calls = 0

    async def classify(self, claim_text: str, context: str):
        from anant.services.claims.classifier import ClassificationResult

        self.calls += 1
        return ClassificationResult(
            epistemic_type=self.label, tokens_used=40, requires_analyst_review=False
        )


def _service(sm, extractor=None, classifier=None):
    from anant.services.claims.service import ClaimService

    return ClaimService(
        sm,
        extractor=extractor or FakeExtractor(),
        classifier=classifier or FakeClassifier(),
    )


@pytest.mark.asyncio
async def test_full_pipeline_extracts_types_and_emits_chained_events(sm) -> None:
    from anant.core.models import Claim, OutboxEvent
    from anant.services.claims.events.constants import CLAIM_EXTRACTED, CLAIM_TYPED

    ws_id, item_id, intake_event_id = await _seed_item(sm)
    service = _service(sm)
    claim_ids = await service.extract_claims_from_intake_item(
        intake_item_id=item_id,
        workspace_id=ws_id,
        causation_event_id=intake_event_id,
        correlation_id="corr-1",
    )
    assert len(claim_ids) == 2

    async with sm() as session:
        claims = (
            await session.execute(
                select(Claim).where(Claim.workspace_id == ws_id)
            )
        ).scalars().all()
        assert len(claims) == 2
        assert all(c.epistemic_type == "claim" for c in claims)
        assert all(c.classifier_version == 1 for c in claims)
        assert all(c.extractor_version == 1 for c in claims)
        assert all(c.requires_analyst_review is False for c in claims)

        events = (
            await session.execute(
                select(OutboxEvent).where(OutboxEvent.workspace_id == ws_id)
            )
        ).scalars().all()
        extracted = [e for e in events if e.event_name == CLAIM_EXTRACTED]
        typed = [e for e in events if e.event_name == CLAIM_TYPED]
        assert len(extracted) == 2
        assert len(typed) == 2

        # Payload + causation chain per spec.
        for e in extracted:
            p = e.event["payload"]
            assert set(p) == {
                "claimId", "intakeItemId", "workspaceId",
                "epistemicTypeHint", "extractorVersion",
            }
            assert p["epistemicTypeHint"] == "unclassified"
            assert e.event["causationId"] == intake_event_id
            assert e.event["correlationId"] == "corr-1"
        extracted_by_claim = {e.event["payload"]["claimId"]: str(e.id) for e in extracted}
        for e in typed:
            p = e.event["payload"]
            assert set(p) == {
                "claimId", "epistemicType", "classifierVersion",
                "workspaceId", "requiresAnalystReview",
            }
            assert p["epistemicType"] == "claim"
            # Causation chain: claim.typed <- its claim.extracted event.
            assert e.event["causationId"] == extracted_by_claim[p["claimId"]]
            assert e.event["correlationId"] == "corr-1"


@pytest.mark.asyncio
async def test_redelivery_is_idempotent(sm) -> None:
    from anant.core.models import Claim, OutboxEvent

    ws_id, item_id, intake_event_id = await _seed_item(sm)
    extractor = FakeExtractor()
    service = _service(sm, extractor=extractor)

    first = await service.extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=intake_event_id, correlation_id=None,
    )
    second = await service.extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=intake_event_id, correlation_id=None,
    )
    assert sorted(first) == sorted(second)
    assert extractor.calls == 1  # second delivery skipped extraction

    async with sm() as session:
        n_claims = len(
            (await session.execute(select(Claim).where(Claim.workspace_id == ws_id)))
            .scalars().all()
        )
        n_events = len(
            (await session.execute(
                select(OutboxEvent).where(OutboxEvent.workspace_id == ws_id)
            )).scalars().all()
        )
    assert n_claims == 2
    # 1 intake event + 2 extracted + 2 typed; nothing duplicated.
    assert n_events == 5


@pytest.mark.asyncio
async def test_redelivery_resumes_unfinished_classification(sm) -> None:
    """Crash between fan-out and typing must not strand claims untyped."""
    from anant.core.models import Claim

    ws_id, item_id, intake_event_id = await _seed_item(sm)

    class ExplodingClassifier(FakeClassifier):
        async def classify(self, claim_text: str, context: str):
            raise RuntimeError("crash mid-typing")

    crashing = _service(sm, classifier=ExplodingClassifier())
    with pytest.raises(RuntimeError):
        await crashing.extract_claims_from_intake_item(
            intake_item_id=item_id, workspace_id=ws_id,
            causation_event_id=intake_event_id, correlation_id=None,
        )

    # Re-delivery: extraction must be skipped, typing must complete.
    resumed = _service(sm, extractor=FakeExtractor(fail_if_called=True))
    await resumed.extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=intake_event_id, correlation_id=None,
    )
    async with sm() as session:
        claims = (
            await session.execute(select(Claim).where(Claim.workspace_id == ws_id))
        ).scalars().all()
        assert claims and all(c.classifier_version == 1 for c in claims)


@pytest.mark.asyncio
async def test_deleted_workspace_dead_letters(sm) -> None:
    from anant.core.models import Workspace
    from anant.services.claims.service import ClaimExtractionHandler
    from anant.services.queue.bus import DomainEvent
    from anant.services.queue.drainer import PermanentDeliveryError

    ws_id, item_id, _ = await _seed_item(sm)
    async with sm() as session:
        await session.execute(
            update(Workspace)
            .where(Workspace.id == ws_id)
            .values(deleted_at=datetime.now(UTC))
        )
        await session.commit()

    from anant.services.intake.events_constants import INTAKE_ITEM_RECEIVED

    handler = ClaimExtractionHandler(sm, service=_service(sm))
    event = DomainEvent(
        id=str(uuid.uuid4()),
        name=INTAKE_ITEM_RECEIVED,
        version=1,
        occurred_at=datetime.now(UTC),
        emitted_at=datetime.now(UTC),
        workspace_id=str(ws_id),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={"workspaceId": str(ws_id), "intakeItemId": str(item_id)},
    )
    with pytest.raises(PermanentDeliveryError):
        await handler(event)


@pytest.mark.asyncio
async def test_missing_normalized_row_is_transient(sm) -> None:
    from anant.core.models import IntakeItemNormalized
    from anant.services.claims.service import NormalizedRowMissingError

    ws_id, item_id, _ = await _seed_item(sm)
    async with sm() as session:
        # Simulate the timing window where normalization hasn't landed.
        from sqlalchemy import delete
        await session.execute(
            delete(IntakeItemNormalized).where(
                IntakeItemNormalized.intake_item_id == item_id
            )
        )
        await session.commit()

    with pytest.raises(NormalizedRowMissingError):
        await _service(sm).extract_claims_from_intake_item(
            intake_item_id=item_id, workspace_id=ws_id,
            causation_event_id=None, correlation_id=None,
        )


@pytest.mark.asyncio
async def test_budget_exhausted_before_extraction_defers(sm) -> None:
    from anant.core.models import WorkspaceAIBudget
    from anant.services.claims.service import BudgetExhaustedError

    ws_id, item_id, _ = await _seed_item(sm)
    async with sm() as session:
        session.add(
            WorkspaceAIBudget(
                workspace_id=ws_id,
                budget_date=datetime.now(UTC).date(),
                tokens_used=100,
                budget_limit=100,
            )
        )
        await session.commit()

    extractor = FakeExtractor(fail_if_called=True)  # AI must be skipped
    with pytest.raises(BudgetExhaustedError):
        await _service(sm, extractor=extractor).extract_claims_from_intake_item(
            intake_item_id=item_id, workspace_id=ws_id,
            causation_event_id=None, correlation_id=None,
        )


@pytest.mark.asyncio
async def test_budget_exhausted_mid_pipeline_flags_claims_for_review(sm) -> None:
    """Extractor spend consumes the whole budget → classification skipped,
    claims stay unclassified with requires_analyst_review, no CLAIM_TYPED."""
    from anant.core.models import Claim, OutboxEvent, WorkspaceAIBudget
    from anant.services.claims.events.constants import CLAIM_TYPED

    ws_id, item_id, intake_event_id = await _seed_item(sm)
    async with sm() as session:
        session.add(
            WorkspaceAIBudget(
                workspace_id=ws_id,
                budget_date=datetime.now(UTC).date(),
                tokens_used=0,
                budget_limit=100,
            )
        )
        await session.commit()

    # 120 tokens of extraction spend > 100 budget → classifier gate closes.
    service = _service(sm, extractor=FakeExtractor(tokens=120))
    await service.extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=intake_event_id, correlation_id=None,
    )

    async with sm() as session:
        claims = (
            await session.execute(select(Claim).where(Claim.workspace_id == ws_id))
        ).scalars().all()
        assert claims
        assert all(c.epistemic_type == "unclassified" for c in claims)
        assert all(c.requires_analyst_review is True for c in claims)
        assert all(c.classifier_version is None for c in claims)

        budget = (
            await session.execute(
                select(WorkspaceAIBudget).where(
                    WorkspaceAIBudget.workspace_id == ws_id
                )
            )
        ).scalars().one()
        assert budget.tokens_used == 120  # extractor spend recorded

        typed = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ws_id,
                    OutboxEvent.event_name == CLAIM_TYPED,
                )
            )
        ).scalars().all()
        assert typed == []  # nothing was typed, nothing is announced


@pytest.mark.asyncio
async def test_classifier_circuit_open_flags_claims_without_typing(sm) -> None:
    """Wave B retrofit: open circuit → claim flagged, unclassified, no TYPED."""
    from anant.core.ai_circuit_breaker import CircuitOpenError
    from anant.core.models import Claim, OutboxEvent
    from anant.services.claims.events.constants import CLAIM_TYPED
    from anant.services.intake.providers.errors import ProviderErrorKind

    ws_id, item_id, intake_event_id = await _seed_item(sm)

    class OpenCircuitClassifier(FakeClassifier):
        async def classify(self, claim_text: str, context: str):
            raise CircuitOpenError(
                kind=ProviderErrorKind.TRANSIENT,
                message="circuit open",
                call_type="classifier",
            )

    await _service(sm, classifier=OpenCircuitClassifier()).extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=intake_event_id, correlation_id=None,
    )
    async with sm() as session:
        claims = (
            await session.execute(select(Claim).where(Claim.workspace_id == ws_id))
        ).scalars().all()
        assert claims
        assert all(c.epistemic_type == "unclassified" for c in claims)
        assert all(c.requires_analyst_review is True for c in claims)
        typed = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ws_id,
                    OutboxEvent.event_name == CLAIM_TYPED,
                )
            )
        ).scalars().all()
        assert typed == []


@pytest.mark.asyncio
async def test_duplicate_claim_text_is_silent_noop(sm) -> None:
    from anant.core.models import Claim
    from anant.services.claims.models import ClaimTriple

    ws_id, item_id, _ = await _seed_item(sm)
    twice = [
        ClaimTriple(subject="A", predicate="says", object=None, text="A says X."),
        ClaimTriple(subject="A", predicate="says", object=None, text="A says X."),
    ]
    await _service(sm, extractor=FakeExtractor(triples=twice)).extract_claims_from_intake_item(
        intake_item_id=item_id, workspace_id=ws_id,
        causation_event_id=None, correlation_id=None,
    )
    async with sm() as session:
        claims = (
            await session.execute(select(Claim).where(Claim.workspace_id == ws_id))
        ).scalars().all()
        assert len(claims) == 1
