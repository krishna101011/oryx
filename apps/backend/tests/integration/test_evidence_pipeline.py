"""Evidence pipeline end-to-end against Postgres (Phase 4 Wave B).

The corpus search runs the REAL BM25/FTS SQL against real tables; only
the AI linker is faked through the service seam.
Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update

pytestmark = pytest.mark.requires_db


@pytest.fixture
def sm():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _seed(sm) -> dict:
    """Workspace + source + claim item + one corpus item that FTS can find.

    Returns ids: workspace, claim (row), claim_item, corpus_item."""
    from anant.core.models import Account, IntakeSource, Workspace
    from anant.services.claims.repository import ClaimsRepository
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    marker = uuid.uuid4().hex[:6]
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"evid+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Evidence WS", owner_account_id=account.id
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

        svc = IntakeService(session)

        async def ingest(subject: str, body: str) -> uuid.UUID:
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                provider_name="rss",
                raw=RawItem(
                    external_id=f"i-{uuid.uuid4().hex[:8]}",
                    received_at=datetime.now(UTC),
                    sender="Example Wire",
                    subject=subject,
                    body_text=body,
                    body_html=None,
                    links=[],
                    payload={},
                ),
            )
            assert res.intake_item_id is not None
            return res.intake_item_id

        claim_item = await ingest(
            f"Quarzite {marker} results",
            f"Quarzite {marker} Corp reported revenue of $5 billion.",
        )
        corpus_item = await ingest(
            f"Quarzite {marker} confirmation",
            f"Filings confirm Quarzite {marker} Corp revenue of $5 billion.",
        )

        claim_id = await ClaimsRepository(session).insert_claim(
            workspace_id=workspace.id,
            intake_item_id=claim_item,
            text=f"Quarzite {marker} Corp reported revenue of $5 billion.",
            subject=f"Quarzite {marker} Corp",
            predicate="reported revenue of",
            object_="$5 billion",
            extractor_version=1,
        )
        assert claim_id is not None
        await session.commit()
        return {
            "workspace": workspace.id,
            "claim": claim_id,
            "claim_item": claim_item,
            "corpus_item": corpus_item,
        }


class FakeLinker:
    version = 1

    def __init__(
        self,
        *,
        evidence_type: str = "corroboration",
        include: bool = True,
        parse_failed: bool = False,
        fail_if_called: bool = False,
        tokens: int = 90,
    ) -> None:
        self.evidence_type = evidence_type
        self.include = include
        self.parse_failed = parse_failed
        self.fail_if_called = fail_if_called
        self.tokens = tokens
        self.calls = 0
        self.last_candidates: list = []

    async def link(self, claim_text: str, candidates: list):
        from anant.services.evidence.linker import LinkingResult
        from anant.services.evidence.models import TYPE_TO_RELATIONSHIP, LinkResult

        if self.fail_if_called:
            raise AssertionError("linker must not be called on this path")
        self.calls += 1
        self.last_candidates = candidates
        if self.parse_failed:
            return LinkingResult(results=[], tokens_used=self.tokens, parse_failed=True)
        results = [
            LinkResult(
                intake_item_id=c.intake_item_id,
                evidence_type=self.evidence_type,
                relationship=TYPE_TO_RELATIONSHIP[self.evidence_type],
                strength=0.8,
                include=self.include,
            )
            for c in candidates
        ]
        return LinkingResult(results=results, tokens_used=self.tokens, parse_failed=False)


def _service(sm, linker=None):
    from anant.services.evidence.service import EvidenceService

    return EvidenceService(sm, linker=linker or FakeLinker())


@pytest.mark.asyncio
async def test_full_pipeline_links_evidence_via_real_fts(sm) -> None:
    from anant.core.models import Claim, ClaimEvidenceLink, Evidence, OutboxEvent
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm)
    linker = FakeLinker()
    evidence_ids = await _service(sm, linker).collect_evidence_for_claim(
        claim_id=ids["claim"],
        workspace_id=ids["workspace"],
        causation_event_id="cause-1",
        correlation_id="corr-1",
    )
    assert len(evidence_ids) == 1
    assert linker.calls == 1
    # The REAL FTS found the corpus item and excluded the claim's own item.
    found_ids = {c.intake_item_id for c in linker.last_candidates}
    assert ids["corpus_item"] in found_ids
    assert ids["claim_item"] not in found_ids
    # Excerpt cap honored on what the linker saw.
    assert all(len(c.body_text_excerpt) <= 500 for c in linker.last_candidates)

    async with sm() as session:
        ev = (
            await session.execute(
                select(Evidence).where(Evidence.workspace_id == ids["workspace"])
            )
        ).scalars().one()
        assert ev.intake_item_id == ids["corpus_item"]
        assert ev.evidence_type == "corroboration"

        link = (
            await session.execute(
                select(ClaimEvidenceLink).where(
                    ClaimEvidenceLink.claim_id == ids["claim"]
                )
            )
        ).scalars().one()
        assert link.relationship == "supports"
        assert link.strength == 0.8
        assert link.linker_version == 1

        claim = await session.get(Claim, ids["claim"])
        assert claim.requires_analyst_review is False  # corroboration ≠ flag

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                )
            )
        ).scalars().all()
        assert len(events) == 1
        payload = events[0].event["payload"]
        assert payload == {
            "claimId": str(ids["claim"]),
            "workspaceId": str(ids["workspace"]),
            "evidenceIds": [str(ev.id)],
            "evidenceCount": 1,
            "searchStrategy": "bm25",
            "linkerVersion": 1,
        }
        assert events[0].event["causationId"] == "cause-1"
        assert events[0].event["correlationId"] == "corr-1"


@pytest.mark.asyncio
async def test_contradiction_flags_claim_for_review(sm) -> None:
    from anant.core.models import Claim

    ids = await _seed(sm)
    await _service(sm, FakeLinker(evidence_type="contradiction")).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        claim = await session.get(Claim, ids["claim"])
        assert claim.requires_analyst_review is True


@pytest.mark.asyncio
async def test_redelivery_is_idempotent(sm) -> None:
    from anant.core.models import ClaimEvidenceLink, OutboxEvent
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm)
    linker = FakeLinker()
    first = await _service(sm, linker).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    second = await _service(sm, linker).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    assert sorted(first) == sorted(second)
    assert linker.calls == 1  # re-delivery short-circuited before the AI call

    async with sm() as session:
        links = (
            await session.execute(
                select(ClaimEvidenceLink).where(
                    ClaimEvidenceLink.claim_id == ids["claim"]
                )
            )
        ).scalars().all()
        assert len(links) == 1
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                )
            )
        ).scalars().all()
        assert len(events) == 1  # not re-emitted


@pytest.mark.asyncio
async def test_zero_candidates_emits_empty_collection(sm) -> None:
    from anant.core.models import OutboxEvent
    from anant.services.claims.repository import ClaimsRepository
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm)
    # A claim whose subject matches nothing in the corpus.
    async with sm() as session:
        lonely_claim = await ClaimsRepository(session).insert_claim(
            workspace_id=ids["workspace"],
            intake_item_id=ids["claim_item"],
            text="Zzyzx Holdings acquired Qwxv Labs.",
            subject="Zzyzx Holdings",
            predicate="acquired",
            object_="Qwxv Labs",
            extractor_version=1,
        )
        await session.commit()

    result = await _service(sm, FakeLinker(fail_if_called=True)).collect_evidence_for_claim(
        claim_id=lonely_claim, workspace_id=ids["workspace"]
    )
    assert result == []
    async with sm() as session:
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["payload"]["evidenceCount"] == 0


@pytest.mark.asyncio
async def test_budget_exhausted_flags_and_emits_zero(sm) -> None:
    from anant.core.models import Claim, OutboxEvent, WorkspaceAIBudget
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm)
    async with sm() as session:
        session.add(
            WorkspaceAIBudget(
                workspace_id=ids["workspace"],
                budget_date=datetime.now(UTC).date(),
                tokens_used=100,
                budget_limit=100,
            )
        )
        await session.commit()

    linker = FakeLinker(fail_if_called=True)  # AI must be skipped
    result = await _service(sm, linker).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    assert result == []
    async with sm() as session:
        claim = await session.get(Claim, ids["claim"])
        assert claim.requires_analyst_review is True
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                )
            )
        ).scalars().all()
        assert events[0].event["payload"]["evidenceCount"] == 0


@pytest.mark.asyncio
async def test_linker_parse_failure_flags_and_emits_zero(sm) -> None:
    from anant.core.models import Claim, WorkspaceAIBudget

    ids = await _seed(sm)
    await _service(sm, FakeLinker(parse_failed=True, tokens=77)).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        claim = await session.get(Claim, ids["claim"])
        assert claim.requires_analyst_review is True
        budget = (
            await session.execute(
                select(WorkspaceAIBudget).where(
                    WorkspaceAIBudget.workspace_id == ids["workspace"]
                )
            )
        ).scalars().one()
        assert budget.tokens_used == 77  # spend recorded despite bad output


@pytest.mark.asyncio
async def test_include_false_creates_no_links_but_emits(sm) -> None:
    from anant.core.models import ClaimEvidenceLink, Evidence, OutboxEvent
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm)
    await _service(sm, FakeLinker(include=False)).collect_evidence_for_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        assert (
            await session.execute(
                select(Evidence).where(Evidence.workspace_id == ids["workspace"])
            )
        ).scalars().all() == []
        assert (
            await session.execute(
                select(ClaimEvidenceLink).where(
                    ClaimEvidenceLink.claim_id == ids["claim"]
                )
            )
        ).scalars().all() == []
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                )
            )
        ).scalars().all()
        assert events[0].event["payload"]["evidenceCount"] == 0


@pytest.mark.asyncio
async def test_deleted_workspace_dead_letters(sm) -> None:
    from anant.core.models import Workspace
    from anant.services.claims.events.constants import CLAIM_TYPED
    from anant.services.evidence.service import EvidenceCollectionHandler
    from anant.services.queue.bus import DomainEvent
    from anant.services.queue.drainer import PermanentDeliveryError

    ids = await _seed(sm)
    async with sm() as session:
        await session.execute(
            update(Workspace)
            .where(Workspace.id == ids["workspace"])
            .values(deleted_at=datetime.now(UTC))
        )
        await session.commit()

    handler = EvidenceCollectionHandler(sm, service=_service(sm))
    event = DomainEvent(
        id=str(uuid.uuid4()),
        name=CLAIM_TYPED,
        version=1,
        occurred_at=datetime.now(UTC),
        emitted_at=datetime.now(UTC),
        workspace_id=str(ids["workspace"]),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={
            "claimId": str(ids["claim"]),
            "workspaceId": str(ids["workspace"]),
        },
    )
    with pytest.raises(PermanentDeliveryError):
        await handler(event)
