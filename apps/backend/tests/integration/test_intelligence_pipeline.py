"""Intelligence composition + conflict projection end-to-end (Wave E)."""
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


async def _seed_item(sm, *, subject: str, claims_spec: list[dict]) -> dict:
    """One intake item + claims. Each claims_spec entry:
    {et, score, outcome, terminal}. terminal=False → no run (blocks fan-in)."""
    from anant.core.models import Account, IntakeSource, VerificationRun, Workspace
    from anant.services.claims.repository import ClaimsRepository
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"intel+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Intel WS", owner_account_id=account.id
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

        res = await IntakeService(session).ingest_raw_item(
            workspace_id=workspace.id,
            intake_source_id=source.id,
            provider_name="rss",
            raw=RawItem(
                external_id=f"i-{uuid.uuid4().hex[:8]}",
                received_at=now,
                sender="Wire Desk",
                subject=subject,
                body_text=f"{subject} body.",
                body_html=None,
                links=[],
                payload={},
            ),
        )
        item_id = res.intake_item_id
        assert item_id is not None

        repo = ClaimsRepository(session)
        claim_ids = []
        for i, spec in enumerate(claims_spec):
            cid = await repo.insert_claim(
                workspace_id=workspace.id,
                intake_item_id=item_id,
                text=f"{subject} fact {i}",
                subject=f"{subject} subj {i}",
                predicate="reported",
                object_=f"value {i}",
                extractor_version=1,
            )
            assert cid is not None
            await repo.set_epistemic_type(
                claim_id=cid,
                epistemic_type=spec.get("et", "claim"),
                classifier_version=1,
                requires_analyst_review=False,
            )
            claim_ids.append(cid)
            if spec.get("terminal", True):
                session.add(
                    VerificationRun(
                        id=uuid.uuid4(),
                        claim_id=cid,
                        status="complete",
                        outcome=spec.get("outcome", "verified"),
                        confidence_score=spec.get("score"),
                        engine_version=1,
                        scoring_version=1,
                        started_at=now,
                        completed_at=now,
                    )
                )
        await session.commit()
        return {
            "account": account.id,
            "workspace": workspace.id,
            "item": item_id,
            "claims": claim_ids,
        }


def _service(sm):
    from anant.services.intelligence.service import IntelligenceService

    return IntelligenceService(sm)


@pytest.mark.asyncio
async def test_composes_when_all_terminal(sm) -> None:
    from anant.core.models import IntelligenceObject, OutboxEvent, VerificationAuditLog
    from anant.services.intelligence.events.constants import OBJECT_CREATED

    ids = await _seed_item(
        sm,
        subject="Acme Q3",
        claims_spec=[
            {"et": "claim", "score": 0.8, "outcome": "verified"},
            {"et": "claim", "score": 0.4, "outcome": "verified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"],
        workspace_id=ids["workspace"],
        causation_event_id="cause-1",
    )
    assert obj_id is not None
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        assert obj.verification_status == "verified"
        assert obj.epistemic_type == "claim"
        assert obj.confidence_score == pytest.approx(0.48)  # 0.4*.6 + 0.6*.4
        assert obj.headline == "Acme Q3"
        assert obj.scoring_version == 1
        assert set(obj.claim_ids) == set(ids["claims"])
        # key_facts is structured (not prose).
        assert len(obj.key_facts) == 2
        any_fact = next(iter(obj.key_facts.values()))
        assert set(any_fact.keys()) == {
            "predicate", "object", "epistemicType", "confidence"
        }

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_CREATED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["causationId"] == "cause-1"
        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.event == "object_created",
                    VerificationAuditLog.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(audit) == 1


@pytest.mark.asyncio
async def test_non_terminal_claim_blocks_composition(sm) -> None:
    from anant.core.models import IntelligenceObject

    ids = await _seed_item(
        sm,
        subject="Pending Co",
        claims_spec=[
            {"et": "claim", "score": 0.8, "outcome": "verified", "terminal": True},
            {"terminal": False},  # no run → not terminal
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    assert obj_id is None  # blocked
    async with sm() as session:
        rows = (
            await session.execute(
                select(IntelligenceObject).where(
                    IntelligenceObject.workspace_id == ids["workspace"]
                )
            )
        ).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_epistemic_type_is_weakest_and_caps_score(sm) -> None:
    from anant.core.models import IntelligenceObject

    ids = await _seed_item(
        sm,
        subject="Mixed",
        claims_spec=[
            {"et": "fact", "score": 0.95, "outcome": "verified"},
            {"et": "opinion", "score": 0.95, "outcome": "verified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        assert obj.epistemic_type == "opinion"
        assert obj.confidence_score == pytest.approx(0.30)  # opinion ceiling


@pytest.mark.asyncio
async def test_idempotent_composition(sm) -> None:
    from anant.core.models import IntelligenceObject, OutboxEvent
    from anant.services.intelligence.events.constants import OBJECT_CREATED

    ids = await _seed_item(
        sm, subject="Once", claims_spec=[{"et": "claim", "score": 0.7}]
    )
    svc = _service(sm)
    first = await svc.compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    second = await svc.compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    assert first == second
    async with sm() as session:
        objs = (
            await session.execute(
                select(IntelligenceObject).where(
                    IntelligenceObject.intake_item_id == ids["item"]
                )
            )
        ).scalars().all()
        assert len(objs) == 1
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_CREATED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1


@pytest.mark.asyncio
async def test_status_unverified_when_not_all_verified(sm) -> None:
    from anant.core.models import IntelligenceObject

    ids = await _seed_item(
        sm,
        subject="Unv",
        claims_spec=[
            {"et": "claim", "score": 0.5, "outcome": "verified"},
            {"et": "claim", "score": 0.5, "outcome": "unverified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        assert obj.verification_status == "unverified"


@pytest.mark.asyncio
async def test_handler_triggers_composition(sm) -> None:
    from anant.core.models import IntelligenceObject
    from anant.services.intelligence.service import CompositionTriggerHandler
    from anant.services.queue.bus import DomainEvent
    from anant.services.verification.events.constants import CLAIM_VERIFIED

    ids = await _seed_item(
        sm, subject="Handler", claims_spec=[{"et": "claim", "score": 0.6}]
    )
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
            "claimId": str(ids["claims"][0]),
            "workspaceId": str(ids["workspace"]),
        },
    )
    await CompositionTriggerHandler(sm)(event)
    async with sm() as session:
        obj = (
            await session.execute(
                select(IntelligenceObject).where(
                    IntelligenceObject.intake_item_id == ids["item"]
                )
            )
        ).scalars().one()
        assert obj.verification_status == "verified"


async def _add_open_conflict(sm, *, workspace_id, claim_a, claim_b, severity=0.9):
    from anant.core.models import ConflictRecord

    a, b = (claim_a, claim_b) if claim_a <= claim_b else (claim_b, claim_a)
    async with sm() as session:
        row = ConflictRecord(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            claim_a_id=a,
            claim_b_id=b,
            conflict_type="direct_contradiction",
            severity=severity,
            status="open",
        )
        session.add(row)
        await session.commit()
        return row.id


def _conflict_event(name, *, workspace_id, claim_a, claim_b, resolution=None):
    from anant.services.queue.bus import DomainEvent

    payload = {
        "claimAId": str(claim_a),
        "claimBId": str(claim_b),
        "workspaceId": str(workspace_id),
    }
    if resolution is not None:
        payload["resolution"] = resolution
    return DomainEvent(
        id=str(uuid.uuid4()),
        name=name,
        version=1,
        occurred_at=datetime.now(UTC),
        emitted_at=datetime.now(UTC),
        workspace_id=str(workspace_id),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload=payload,
    )


@pytest.mark.asyncio
async def test_projector_marks_object_contested_on_detect(sm) -> None:
    from anant.core.models import IntelligenceObject, OutboxEvent
    from anant.services.conflicts.events.constants import CONFLICT_DETECTED
    from anant.services.intelligence.events.constants import OBJECT_UPDATED
    from anant.services.intelligence.service import ObjectConflictProjector

    ids = await _seed_item(
        sm,
        subject="ConflictItem",
        claims_spec=[
            {"et": "claim", "score": 0.8, "outcome": "verified"},
            {"et": "claim", "score": 0.7, "outcome": "verified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    await _add_open_conflict(
        sm, workspace_id=ids["workspace"], claim_a=ids["claims"][0], claim_b=ids["claims"][1]
    )
    await ObjectConflictProjector(sm)(
        _conflict_event(
            CONFLICT_DETECTED,
            workspace_id=ids["workspace"],
            claim_a=ids["claims"][0],
            claim_b=ids["claims"][1],
        )
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        assert obj.verification_status == "contested"
        assert len(obj.conflict_ids) == 1
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_UPDATED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].event["payload"]["changeType"] == "conflict_detected"


@pytest.mark.asyncio
async def test_projector_recomposes_on_resolve(sm) -> None:
    from anant.core.models import Claim, IntelligenceObject, OutboxEvent
    from anant.services.conflicts.events.constants import (
        CONFLICT_DETECTED,
        CONFLICT_RESOLVED,
    )
    from anant.services.intelligence.events.constants import OBJECT_REVIEWED
    from anant.services.intelligence.service import ObjectConflictProjector

    ids = await _seed_item(
        sm,
        subject="ResolveItem",
        claims_spec=[
            {"et": "claim", "score": 0.8, "outcome": "verified"},
            {"et": "claim", "score": 0.7, "outcome": "verified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    conflict_id = await _add_open_conflict(
        sm, workspace_id=ids["workspace"], claim_a=ids["claims"][0], claim_b=ids["claims"][1]
    )
    proj = ObjectConflictProjector(sm)
    await proj(
        _conflict_event(
            CONFLICT_DETECTED,
            workspace_id=ids["workspace"],
            claim_a=ids["claims"][0],
            claim_b=ids["claims"][1],
        )
    )
    # Analyst resolves: supersede claim_b, close the conflict.
    from anant.core.models import ConflictRecord

    async with sm() as session:
        await session.execute(
            update(Claim)
            .where(Claim.id == ids["claims"][1])
            .values(superseded_by=ids["claims"][0])
        )
        await session.execute(
            update(ConflictRecord)
            .where(ConflictRecord.id == conflict_id)
            .values(status="resolved_a_wins")
        )
        await session.commit()

    await proj(
        _conflict_event(
            CONFLICT_RESOLVED,
            workspace_id=ids["workspace"],
            claim_a=ids["claims"][0],
            claim_b=ids["claims"][1],
            resolution="analyst",
        )
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        # No open conflict remains; superseded claim excluded → verified.
        assert obj.verification_status == "verified"
        assert obj.claim_ids == [ids["claims"][0]]
        reviewed = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_REVIEWED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(reviewed) == 1  # analyst resolution emits OBJECT_REVIEWED


@pytest.mark.asyncio
async def test_review_object_flips_status_and_emits(sm) -> None:
    from anant.core.models import AnalystReview, IntelligenceObject, OutboxEvent
    from anant.services.intelligence.events.constants import OBJECT_REVIEWED
    from anant.services.review.service import ReviewService

    ids = await _seed_item(
        sm, subject="ReviewMe", claims_spec=[{"et": "claim", "score": 0.6}]
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    await ReviewService(sm).review_object(
        object_id=obj_id,
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="approved",
        note="Composite reads correctly.",
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        assert obj.verification_status == "analyst_approved"
        review = (
            await session.execute(
                select(AnalystReview).where(AnalystReview.entity_id == obj_id)
            )
        ).scalars().one()
        assert review.entity_type == "intelligence_object"
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_REVIEWED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 1


@pytest.mark.asyncio
async def test_sticky_analyst_status_survives_recompose(sm) -> None:
    from anant.core.models import IntelligenceObject
    from anant.services.conflicts.events.constants import CONFLICT_DETECTED
    from anant.services.intelligence.service import ObjectConflictProjector
    from anant.services.review.service import ReviewService

    ids = await _seed_item(
        sm,
        subject="Sticky",
        claims_spec=[
            {"et": "claim", "score": 0.8, "outcome": "verified"},
            {"et": "claim", "score": 0.7, "outcome": "verified"},
        ],
    )
    obj_id = await _service(sm).compose_for_item(
        intake_item_id=ids["item"], workspace_id=ids["workspace"]
    )
    await ReviewService(sm).review_object(
        object_id=obj_id,
        workspace_id=ids["workspace"],
        account_id=ids["account"],
        outcome="rejected",
        note="Not credible.",
    )
    await _add_open_conflict(
        sm, workspace_id=ids["workspace"], claim_a=ids["claims"][0], claim_b=ids["claims"][1]
    )
    await ObjectConflictProjector(sm)(
        _conflict_event(
            CONFLICT_DETECTED,
            workspace_id=ids["workspace"],
            claim_a=ids["claims"][0],
            claim_b=ids["claims"][1],
        )
    )
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        # Recompose preserved the analyst verdict.
        assert obj.verification_status == "analyst_rejected"


@pytest.mark.asyncio
async def test_deleted_workspace_dead_letters(sm) -> None:
    from anant.core.models import Workspace
    from anant.services.intelligence.service import CompositionTriggerHandler
    from anant.services.queue.bus import DomainEvent
    from anant.services.queue.drainer import PermanentDeliveryError
    from anant.services.verification.events.constants import CLAIM_VERIFIED

    ids = await _seed_item(
        sm, subject="Dead", claims_spec=[{"et": "claim", "score": 0.6}]
    )
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
            "claimId": str(ids["claims"][0]),
            "workspaceId": str(ids["workspace"]),
        },
    )
    with pytest.raises(PermanentDeliveryError):
        await CompositionTriggerHandler(sm)(event)
