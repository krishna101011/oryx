"""Conflict detection + resolution end-to-end against Postgres (Wave D).

The auto-resolver and the analyst-resolution paths run over real tables. The
AI detector is faked through the service seam (PATH B); PATH A uses a real
contradiction evidence link and no AI at all.

Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update

from anant.services.conflicts.models import ConflictResult

pytestmark = pytest.mark.requires_db


@pytest.fixture
def sm():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(os.environ["ANANT_TEST_DB"])
    return async_sessionmaker(bind=engine, expire_on_commit=False)


class FakeDetector:
    """Stands in for ConflictDetectorAI on PATH B."""

    version = 1

    def __init__(
        self,
        *,
        is_conflict: bool = True,
        conflict_type: str = "factual_disagreement",
        severity: float = 0.1,
        tokens: int = 0,
    ) -> None:
        self._result = ConflictResult(
            is_conflict=is_conflict,
            conflict_type=conflict_type,
            severity=severity,
            reasoning="fake",
        )
        self._tokens = tokens
        self.calls = 0

    async def detect(self, **kwargs):
        from anant.services.conflicts.detector import DetectionResult

        self.calls += 1
        return DetectionResult(result=self._result, tokens_used=self._tokens)


async def _seed(
    sm,
    *,
    score_a: float = 0.8,
    score_b: float = 0.2,
    same_predicate: bool = False,
    with_contradiction_link: bool = False,
    contradiction_strength: float = 0.9,
) -> dict:
    from anant.core.models import (
        Account,
        ClaimEvidenceLink,
        Evidence,
        IntakeSource,
        VerificationRun,
        Workspace,
    )
    from anant.services.claims.repository import ClaimsRepository
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"conf+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Conflict WS", owner_account_id=account.id
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

        async def ingest(subject: str) -> uuid.UUID:
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                provider_name="rss",
                raw=RawItem(
                    external_id=f"i-{uuid.uuid4().hex[:8]}",
                    received_at=now,
                    sender="Wire",
                    subject=subject,
                    body_text=f"{subject} body.",
                    body_html=None,
                    links=[],
                    payload={},
                ),
            )
            assert res.intake_item_id is not None
            return res.intake_item_id

        item_a = await ingest("Acme A")
        item_b = await ingest("Acme B")

        repo = ClaimsRepository(session)

        async def make_claim(item_id, predicate, obj) -> uuid.UUID:
            cid = await repo.insert_claim(
                workspace_id=workspace.id,
                intake_item_id=item_id,
                text=f"Acme Corp {predicate} {obj}.",
                subject="Acme Corp",
                predicate=predicate,
                object_=obj,
                extractor_version=1,
            )
            assert cid is not None
            await repo.set_epistemic_type(
                claim_id=cid,
                epistemic_type="claim",
                classifier_version=1,
                requires_analyst_review=False,
            )
            return cid

        pred_b = "reported revenue of" if same_predicate else "reported a loss of"
        claim_a = await make_claim(item_a, "reported revenue of", "$5 billion")
        claim_b = await make_claim(item_b, pred_b, "$2 billion")

        def run(claim_id, score):
            return VerificationRun(
                id=uuid.uuid4(),
                claim_id=claim_id,
                status="complete",
                outcome="verified",
                confidence_score=score,
                engine_version=1,
                scoring_version=1,
                started_at=now,
                completed_at=now,
            )

        session.add_all([run(claim_a, score_a), run(claim_b, score_b)])

        if with_contradiction_link:
            ev = Evidence(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                intake_item_id=item_b,  # evidence drawn from claim_b's item
                evidence_type="contradiction",
                text="contradicts claim A",
            )
            session.add(ev)
            await session.flush()
            session.add(
                ClaimEvidenceLink(
                    claim_id=claim_a,
                    evidence_id=ev.id,
                    relationship="contradicts",
                    strength=contradiction_strength,
                    linker_version=1,
                )
            )

        await session.commit()
        return {
            "account": account.id,
            "workspace": workspace.id,
            "source": source.id,
            "claim_a": claim_a,
            "claim_b": claim_b,
        }


def _service(sm, detector=None):
    from anant.services.conflicts.service import ConflictService

    return ConflictService(sm, detector=detector or FakeDetector())


@pytest.mark.asyncio
async def test_path_b_ai_conflict_auto_resolves(sm) -> None:
    from anant.core.models import Claim, ConflictRecord, OutboxEvent, VerificationAuditLog
    from anant.services.conflicts.events.constants import CONFLICT_RESOLVED

    ids = await _seed(sm, score_a=0.8, score_b=0.2)
    detector = FakeDetector(conflict_type="factual_disagreement", severity=0.1)
    await _service(sm, detector).detect_for_claim(
        claim_id=ids["claim_b"],
        workspace_id=ids["workspace"],
        causation_event_id="cause-1",
        correlation_id="corr-1",
    )
    assert detector.calls == 1

    async with sm() as session:
        conflict = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().one()
        assert conflict.status == "resolved_system"
        assert conflict.resolved_by_kind == "system"
        assert conflict.conflict_type == "factual_disagreement"
        # Canonical ordering: claim_a_id is the smaller UUID.
        assert conflict.claim_a_id < conflict.claim_b_id

        # Loser (score 0.2 = claim_b) is superseded by winner (claim_a).
        loser = await session.get(Claim, ids["claim_b"])
        assert loser.superseded_by == ids["claim_a"]
        winner = await session.get(Claim, ids["claim_a"])
        assert winner.superseded_by is None

        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.event == "conflict_resolved",
                    VerificationAuditLog.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(audit) == 1
        assert audit[0].data["resolution"] == "system"
        assert audit[0].data["winner_id"] == str(ids["claim_a"])

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == CONFLICT_RESOLVED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["payload"]["resolution"] == "system"
        assert events[0].event["causationId"] == "cause-1"


@pytest.mark.asyncio
async def test_path_a_contradiction_link_escalates(sm) -> None:
    from anant.core.models import Claim, ConflictRecord, OutboxEvent
    from anant.services.conflicts.events.constants import CONFLICT_DETECTED

    ids = await _seed(sm, with_contradiction_link=True, contradiction_strength=0.9)
    # Real detector instance, but PATH A must NOT call it.
    detector = FakeDetector()
    await _service(sm, detector).detect_for_claim(
        claim_id=ids["claim_a"], workspace_id=ids["workspace"]
    )
    assert detector.calls == 0  # contradiction link → no AI

    async with sm() as session:
        conflict = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().one()
        assert conflict.conflict_type == "direct_contradiction"
        assert conflict.severity == 0.9
        assert conflict.status == "open"  # severity 0.9 ≥ 0.3 → escalated

        for cid in (ids["claim_a"], ids["claim_b"]):
            claim = await session.get(Claim, cid)
            assert claim.requires_analyst_review is True
            assert claim.superseded_by is None  # escalation supersedes nothing

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == CONFLICT_DETECTED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1


@pytest.mark.asyncio
async def test_redetection_is_idempotent(sm) -> None:
    from anant.core.models import ConflictRecord, OutboxEvent
    from anant.services.conflicts.events.constants import CONFLICT_DETECTED

    ids = await _seed(sm, with_contradiction_link=True)
    svc = _service(sm)
    await svc.detect_for_claim(claim_id=ids["claim_a"], workspace_id=ids["workspace"])
    await svc.detect_for_claim(claim_id=ids["claim_a"], workspace_id=ids["workspace"])

    async with sm() as session:
        conflicts = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().all()
        assert len(conflicts) == 1
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == CONFLICT_DETECTED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1


async def _make_open_conflict(sm) -> dict:
    """An escalated (open) conflict via PATH A, ready for analyst resolution."""
    ids = await _seed(sm, with_contradiction_link=True, contradiction_strength=0.9)
    await _service(sm).detect_for_claim(
        claim_id=ids["claim_a"], workspace_id=ids["workspace"]
    )
    from anant.core.models import ConflictRecord

    async with sm() as session:
        conflict = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().one()
        ids["conflict"] = conflict.id
        ids["conflict_a"] = conflict.claim_a_id
        ids["conflict_b"] = conflict.claim_b_id
    return ids


def _review(sm):
    from anant.services.review.service import ReviewService

    return ReviewService(sm)


@pytest.mark.asyncio
async def test_analyst_resolve_a_wins(sm) -> None:
    from anant.core.models import (
        AnalystReview,
        Claim,
        ConflictRecord,
        OutboxEvent,
        VerificationAuditLog,
    )
    from anant.services.conflicts.events.constants import CONFLICT_RESOLVED

    ids = await _make_open_conflict(sm)
    result = await _review(sm).resolve_conflict(
        conflict_id=ids["conflict"],
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="a_wins",
        note="Filing A supersedes the rumor in B.",
    )
    assert result["status"] == "resolved_a_wins"

    async with sm() as session:
        conflict = await session.get(ConflictRecord, ids["conflict"])
        assert conflict.status == "resolved_a_wins"
        assert conflict.resolved_by == ids["account"]
        assert conflict.resolved_by_kind == "analyst"
        assert conflict.resolution_note == "Filing A supersedes the rumor in B."

        loser = await session.get(Claim, ids["conflict_b"])
        assert loser.superseded_by == ids["conflict_a"]

        review = (
            await session.execute(
                select(AnalystReview).where(
                    AnalystReview.workspace_id == ids["workspace"]
                )
            )
        ).scalars().one()
        assert review.entity_type == "conflict"
        assert review.outcome == "conflict_resolved_a"
        assert review.account_id == ids["account"]

        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.event == "analyst_override",
                    VerificationAuditLog.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(audit) == 1

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == CONFLICT_RESOLVED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["payload"]["resolution"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_resolve_empty_note_rejected(sm) -> None:
    from anant.core.errors import BadRequestError

    ids = await _make_open_conflict(sm)
    with pytest.raises(BadRequestError):
        await _review(sm).resolve_conflict(
            conflict_id=ids["conflict"],
            workspace_id=ids["workspace"],
            account_id=ids["account"],
            outcome="a_wins",
            note="",
        )


@pytest.mark.asyncio
async def test_review_claim_records_without_mutation(sm) -> None:
    from anant.core.models import AnalystReview, Claim

    ids = await _seed(sm)
    before = None
    async with sm() as session:
        before = await session.get(Claim, ids["claim_a"])
        before_review_flag = before.requires_analyst_review
        before_type = before.epistemic_type

    await _review(sm).review_claim(
        claim_id=ids["claim_a"],
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="flagged",
        note="Needs a second look.",
    )

    async with sm() as session:
        review = (
            await session.execute(
                select(AnalystReview).where(
                    AnalystReview.entity_id == ids["claim_a"]
                )
            )
        ).scalars().one()
        assert review.entity_type == "claim"
        assert review.outcome == "flagged"

        claim = await session.get(Claim, ids["claim_a"])
        # The claim row is untouched by the override.
        assert claim.requires_analyst_review == before_review_flag
        assert claim.epistemic_type == before_type


@pytest.mark.asyncio
async def test_queue_lists_pending_and_open(sm) -> None:
    ids = await _make_open_conflict(sm)
    queue = await _review(sm).get_queue(ids["workspace"])
    assert len(queue["openConflicts"]) == 1
    assert queue["openConflicts"][0].id == ids["conflict"]
    pending_ids = {c.id for c in queue["pendingClaims"]}
    assert ids["conflict_a"] in pending_ids
    assert ids["conflict_b"] in pending_ids


@pytest.mark.asyncio
async def test_same_predicate_no_conflict(sm) -> None:
    from anant.core.models import ConflictRecord

    ids = await _seed(sm, same_predicate=True)
    detector = FakeDetector()
    await _service(sm, detector).detect_for_claim(
        claim_id=ids["claim_b"], workspace_id=ids["workspace"]
    )
    assert detector.calls == 0  # identical predicates → no AI, no conflict
    async with sm() as session:
        rows = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_ai_reports_no_conflict(sm) -> None:
    from anant.core.models import ConflictRecord

    ids = await _seed(sm)
    detector = FakeDetector(is_conflict=False)
    await _service(sm, detector).detect_for_claim(
        claim_id=ids["claim_b"], workspace_id=ids["workspace"]
    )
    assert detector.calls == 1
    async with sm() as session:
        rows = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_unverified_claim_is_not_a_candidate(sm) -> None:
    """A peer without a completed verification run is never compared."""
    from anant.core.models import ConflictRecord, VerificationRun

    ids = await _seed(sm, with_contradiction_link=True)
    # Drop claim_b's completed run so it no longer qualifies as a candidate.
    async with sm() as session:
        await session.execute(
            update(VerificationRun)
            .where(VerificationRun.claim_id == ids["claim_b"])
            .values(status="pending")
        )
        await session.commit()

    await _service(sm).detect_for_claim(
        claim_id=ids["claim_a"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        rows = (
            await session.execute(
                select(ConflictRecord).where(
                    ConflictRecord.workspace_id == ids["workspace"]
                )
            )
        ).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_analyst_resolve_b_wins(sm) -> None:
    from anant.core.models import Claim, ConflictRecord

    ids = await _make_open_conflict(sm)
    await _review(sm).resolve_conflict(
        conflict_id=ids["conflict"],
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="b_wins",
        note="B is the primary source.",
    )
    async with sm() as session:
        conflict = await session.get(ConflictRecord, ids["conflict"])
        assert conflict.status == "resolved_b_wins"
        winner_loser = await session.get(Claim, ids["conflict_a"])
        assert winner_loser.superseded_by == ids["conflict_b"]


@pytest.mark.asyncio
async def test_analyst_resolve_inconclusive_supersedes_nothing(sm) -> None:
    from anant.core.models import AnalystReview, Claim, ConflictRecord

    ids = await _make_open_conflict(sm)
    await _review(sm).resolve_conflict(
        conflict_id=ids["conflict"],
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="inconclusive",
        note="Cannot determine from available evidence.",
    )
    async with sm() as session:
        conflict = await session.get(ConflictRecord, ids["conflict"])
        assert conflict.status == "resolved_inconclusive"
        for cid in (ids["conflict_a"], ids["conflict_b"]):
            claim = await session.get(Claim, cid)
            assert claim.superseded_by is None
        review = (
            await session.execute(
                select(AnalystReview).where(
                    AnalystReview.entity_id == ids["conflict"]
                )
            )
        ).scalars().one()
        assert review.outcome == "conflict_inconclusive"


@pytest.mark.asyncio
async def test_review_object_records_analyst_review(sm) -> None:
    from anant.core.models import AnalystReview, VerificationAuditLog

    ids = await _seed(sm)
    object_id = uuid.uuid4()
    await _review(sm).review_object(
        object_id=object_id,
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="approved",
        note="Composite reads correctly.",
    )
    async with sm() as session:
        review = (
            await session.execute(
                select(AnalystReview).where(AnalystReview.entity_id == object_id)
            )
        ).scalars().one()
        assert review.entity_type == "intelligence_object"
        assert review.outcome == "approved"
        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.entity_id == object_id,
                    VerificationAuditLog.event == "analyst_override",
                )
            )
        ).scalars().all()
        assert len(audit) == 1


@pytest.mark.asyncio
async def test_deleted_workspace_dead_letters(sm) -> None:
    from anant.core.models import Workspace
    from anant.services.conflicts.service import ConflictDetectionHandler
    from anant.services.queue.bus import DomainEvent
    from anant.services.queue.drainer import PermanentDeliveryError
    from anant.services.verification.events.constants import CLAIM_VERIFIED

    ids = await _seed(sm)
    async with sm() as session:
        await session.execute(
            update(Workspace)
            .where(Workspace.id == ids["workspace"])
            .values(deleted_at=datetime.now(UTC))
        )
        await session.commit()

    event = DomainEvent(
        id=str(uuid.uuid4()),
        name=CLAIM_VERIFIED,
        version=1,
        occurred_at=datetime.now(UTC),
        emitted_at=datetime.now(UTC),
        workspace_id=str(ids["workspace"]),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={
            "claimId": str(ids["claim_a"]),
            "workspaceId": str(ids["workspace"]),
        },
    )
    with pytest.raises(PermanentDeliveryError):
        await ConflictDetectionHandler(sm)(event)
