"""Verification pipeline end-to-end against Postgres (Phase 4 Wave C).

The engine and scorer are pure (no AI), so nothing is faked here — this
drives the REAL service over real tables: claim + evidence links in, a
verification_run + credibility update + audit row + CLAIM_VERIFIED out.

Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update

pytestmark = pytest.mark.requires_db


async def _seed(sm, *, epistemic_type: str = "claim", with_link: bool = True) -> dict:
    """Workspace + source + one ingested item + a typed claim, optionally with
    one corroborating evidence link. Returns the ids the tests assert on."""
    from anant.core.models import (
        Account,
        ClaimEvidenceLink,
        Evidence,
        IntakeSource,
        Workspace,
    )
    from anant.services.claims.repository import ClaimsRepository
    from anant.services.intake.providers.base import RawItem
    from anant.services.intake.service import IntakeService

    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"verif+{uuid.uuid4().hex[:8]}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Verify WS", owner_account_id=account.id
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
        res = await svc.ingest_raw_item(
            workspace_id=workspace.id,
            intake_source_id=source.id,
            provider_name="rss",
            raw=RawItem(
                external_id=f"i-{uuid.uuid4().hex[:8]}",
                received_at=datetime.now(UTC),
                sender="Example Wire",
                subject="Acme results",
                body_text="Acme Corp reported revenue of $5 billion.",
                body_html=None,
                links=[],
                payload={},
            ),
        )
        assert res.intake_item_id is not None
        item_id = res.intake_item_id

        repo = ClaimsRepository(session)
        claim_id = await repo.insert_claim(
            workspace_id=workspace.id,
            intake_item_id=item_id,
            text="Acme Corp reported revenue of $5 billion.",
            subject="Acme Corp",
            predicate="reported revenue of",
            object_="$5 billion",
            extractor_version=1,
        )
        assert claim_id is not None
        await repo.set_epistemic_type(
            claim_id=claim_id,
            epistemic_type=epistemic_type,
            classifier_version=1,
            requires_analyst_review=False,
        )

        if with_link:
            evidence = Evidence(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                intake_item_id=item_id,
                evidence_type="corroboration",
                text="A filing corroborates Acme Corp revenue of $5 billion.",
            )
            session.add(evidence)
            await session.flush()
            session.add(
                ClaimEvidenceLink(
                    claim_id=claim_id,
                    evidence_id=evidence.id,
                    relationship="supports",
                    strength=0.8,
                    linker_version=1,
                )
            )

        await session.commit()
        return {
            "workspace": workspace.id,
            "source": source.id,
            "item": item_id,
            "claim": claim_id,
        }


def _service(sm):
    from anant.services.verification.service import VerificationService

    return VerificationService(sm)


@pytest.mark.asyncio
async def test_supported_claim_verifies_and_updates_credibility(sm) -> None:
    from anant.core.models import (
        OutboxEvent,
        SourceCredibilityRecord,
        VerificationAuditLog,
        VerificationRun,
    )
    from anant.services.verification.events.constants import CLAIM_VERIFIED

    ids = await _seed(sm)
    run_id = await _service(sm).verify_claim(
        claim_id=ids["claim"],
        workspace_id=ids["workspace"],
        causation_event_id="cause-1",
        correlation_id="corr-1",
    )
    assert run_id is not None

    async with sm() as session:
        run = (
            await session.execute(
                select(VerificationRun).where(VerificationRun.id == run_id)
            )
        ).scalars().one()
        assert run.status == "complete"
        assert run.outcome == "verified"
        assert run.engine_version == 1
        assert run.scoring_version == 1
        assert run.cross_reference_count == 1  # one "supports" link
        assert run.primary_source_flag is False  # corroboration, not primary
        assert run.confidence_score is not None
        assert 0.0 < run.confidence_score <= 0.85  # claim ceiling (ADR-036)
        assert run.completed_at is not None

        cred = (
            await session.execute(
                select(SourceCredibilityRecord).where(
                    SourceCredibilityRecord.workspace_id == ids["workspace"],
                    SourceCredibilityRecord.source_id == ids["source"],
                )
            )
        ).scalars().one()
        # Neutral prior 0.5 nudged toward 1.0 by ALPHA=0.1 on a verified outcome.
        assert cred.accuracy_rate == pytest.approx(0.55)
        assert cred.verified_claim_count == 1
        assert cred.contested_claim_count == 0
        assert cred.total_claim_count == 1
        assert cred.last_evaluated_at is not None

        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.workspace_id == ids["workspace"],
                    VerificationAuditLog.entity_id == ids["claim"],
                )
            )
        ).scalars().all()
        assert len(audit) == 1
        assert audit[0].event == "verification_complete"
        assert audit[0].data["outcome"] == "verified"

        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == CLAIM_VERIFIED,
                )
            )
        ).scalars().all()
        assert len(events) == 1
        payload = events[0].event["payload"]
        assert payload["claimId"] == str(ids["claim"])
        assert payload["verificationRunId"] == str(run_id)
        assert payload["outcome"] == "verified"
        assert payload["engineVersion"] == 1
        assert payload["scoringVersion"] == 1
        assert payload["workspaceId"] == str(ids["workspace"])
        assert events[0].event["causationId"] == "cause-1"
        assert events[0].event["correlationId"] == "corr-1"


@pytest.mark.asyncio
async def test_redelivery_is_idempotent(sm) -> None:
    from anant.core.models import (
        OutboxEvent,
        SourceCredibilityRecord,
        VerificationRun,
    )
    from anant.services.verification.events.constants import CLAIM_VERIFIED

    ids = await _seed(sm)
    first = await _service(sm).verify_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    second = await _service(sm).verify_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    assert first == second  # same run id; no second pass

    async with sm() as session:
        runs = (
            await session.execute(
                select(VerificationRun).where(VerificationRun.claim_id == ids["claim"])
            )
        ).scalars().all()
        assert len(runs) == 1
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == CLAIM_VERIFIED,
                )
            )
        ).scalars().all()
        assert len(events) == 1  # not re-emitted
        cred = (
            await session.execute(
                select(SourceCredibilityRecord).where(
                    SourceCredibilityRecord.source_id == ids["source"]
                )
            )
        ).scalars().one()
        assert cred.total_claim_count == 1  # credibility not double-counted


@pytest.mark.asyncio
async def test_evidence_collected_event_drives_verification(sm) -> None:
    """The EVIDENCE_COLLECTED → verified wiring, through the handler."""
    from anant.core.models import OutboxEvent, VerificationRun
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED
    from anant.services.queue.bus import DomainEvent
    from anant.services.verification.events.constants import CLAIM_VERIFIED
    from anant.services.verification.service import VerificationHandler

    ids = await _seed(sm)
    event = DomainEvent(
        id=str(uuid.uuid4()),
        name=EVIDENCE_COLLECTED,
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
            "evidenceIds": [],
            "evidenceCount": 1,
        },
    )
    await VerificationHandler(sm)(event)

    async with sm() as session:
        run = (
            await session.execute(
                select(VerificationRun).where(VerificationRun.claim_id == ids["claim"])
            )
        ).scalars().one()
        assert run.status == "complete"
        assert run.outcome == "verified"
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == ids["workspace"],
                    OutboxEvent.event_name == CLAIM_VERIFIED,
                )
            )
        ).scalars().all()
        assert len(events) == 1
        # causationId chains to the consumed event's id (ADR-014).
        assert events[0].event["causationId"] == event.id


@pytest.mark.asyncio
async def test_unclassified_claim_is_unverifiable_without_score(sm) -> None:
    from anant.core.models import VerificationRun

    # No epistemic type set, no evidence — the unscorable path.
    ids = await _seed(sm, epistemic_type="unclassified", with_link=False)
    run_id = await _service(sm).verify_claim(
        claim_id=ids["claim"], workspace_id=ids["workspace"]
    )
    async with sm() as session:
        run = (
            await session.execute(
                select(VerificationRun).where(VerificationRun.id == run_id)
            )
        ).scalars().one()
        assert run.outcome == "unverifiable"
        assert run.confidence_score is None  # no ceiling → no score (ADR-036)


@pytest.mark.asyncio
async def test_deleted_workspace_dead_letters(sm) -> None:
    from anant.core.models import Workspace
    from anant.services.evidence.events.constants import EVIDENCE_COLLECTED
    from anant.services.queue.bus import DomainEvent
    from anant.services.queue.drainer import PermanentDeliveryError
    from anant.services.verification.service import VerificationHandler

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
        name=EVIDENCE_COLLECTED,
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
        await VerificationHandler(sm)(event)
