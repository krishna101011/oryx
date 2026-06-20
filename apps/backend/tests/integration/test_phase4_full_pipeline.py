"""Phase 4 end-to-end proof: intake.item.received → research.packet.ready.

One test drives the whole pipeline with the AI seams faked, asserting at each
hop and verifying the causation chain, the no-AI / no-write boundaries, and
that consumed_at stays NULL (Phase 5 owns it).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


# ---------------- AI fakes (the only fakes; everything else is real) ----------


class _FakeExtractor:
    version = 1

    def __init__(self, triples):
        self._triples = triples

    async def extract(self, body_text):
        from oryx.services.claims.extractor import ExtractionResult

        return ExtractionResult(triples=self._triples, tokens_used=12, parse_failed=False)


class _FakeClassifier:
    version = 1

    async def classify(self, claim_text, context):
        from oryx.services.claims.classifier import ClassificationResult

        return ClassificationResult(
            epistemic_type="claim", tokens_used=4, requires_analyst_review=False
        )


class _FakeLinker:
    version = 1

    async def link(self, claim_text, candidates):
        from oryx.services.evidence.linker import LinkingResult
        from oryx.services.evidence.models import TYPE_TO_RELATIONSHIP, LinkResult

        results = [
            LinkResult(
                intake_item_id=c.intake_item_id,
                evidence_type="corroboration",
                relationship=TYPE_TO_RELATIONSHIP["corroboration"],
                strength=0.8,
                include=True,
            )
            for c in candidates
        ]
        return LinkingResult(results=results, tokens_used=30, parse_failed=False)


async def _event(session, name, *, claim_id=None):
    """Latest outbox envelope for an event name, optionally filtered by claimId."""
    from oryx.core.models import OutboxEvent

    rows = (
        await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.event_name == name)
            .order_by(OutboxEvent.created_at.desc())
        )
    ).scalars().all()
    for r in rows:
        if claim_id is None or r.event["payload"].get("claimId") == str(claim_id):
            return r.event
    return None


@pytest.mark.asyncio
async def test_full_pipeline_intake_to_packet(sm) -> None:
    from oryx.core.models import (
        Account,
        Claim,
        IntakeItem,
        IntakeItemNormalized,
        IntakeSource,
        IntelligenceObject,
        SourceCredibilityRecord,
        Workspace,
    )
    from oryx.services.claims.events.constants import CLAIM_EXTRACTED, CLAIM_TYPED
    from oryx.services.claims.models import ClaimTriple
    from oryx.services.claims.service import ClaimService
    from oryx.services.evidence.events.constants import EVIDENCE_COLLECTED
    from oryx.services.evidence.service import EvidenceService
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService
    from oryx.services.intelligence.events.constants import OBJECT_CREATED
    from oryx.services.intelligence.service import IntelligenceService
    from oryx.services.queue.outbox import enqueue_event
    from oryx.services.research.events.constants import PACKET_READY
    from oryx.services.research.service import ResearchService
    from oryx.services.verification.events.constants import CLAIM_VERIFIED
    from oryx.services.verification.service import VerificationService

    now = datetime.now(UTC)

    # ---- Setup: workspace + source + credibility + two intake items ----
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"e2e+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(id=uuid.uuid4(), name="E2E", owner_account_id=account.id)
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
        session.add(
            SourceCredibilityRecord(
                workspace_id=workspace.id, source_id=source.id, accuracy_rate=0.7
            )
        )

        marker = uuid.uuid4().hex[:6]
        svc = IntakeService(session)

        async def ingest(subject, body):
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                provider_name="rss",
                raw=RawItem(
                    external_id=f"i-{uuid.uuid4().hex[:8]}",
                    received_at=now,
                    sender="Wire Desk",
                    subject=subject,
                    body_text=body,
                    body_html=None,
                    links=[],
                    payload={},
                ),
            )
            assert res.intake_item_id is not None
            return res.intake_item_id

        item_a = await ingest(
            f"Zentech {marker} earnings",
            f"Zentech {marker} Corp raised five billion dollars this quarter.",
        )
        item_b = await ingest(
            f"Zentech {marker} confirmation",
            f"Filings confirm Zentech {marker} Corp raised five billion dollars.",
        )
        workspace_id = workspace.id
        await session.commit()

    subj_a = f"Zentech {marker} Corp"
    triples = [
        ClaimTriple(
            subject=subj_a,
            predicate="raised",
            object="five billion dollars",
            text=f"Zentech {marker} Corp raised five billion dollars this quarter.",
        ),
    ]

    # ---- Step 1: synthetic intake.item.received (the chain root) ----
    from oryx.services.intake.events_constants import INTAKE_ITEM_RECEIVED

    async with sm() as session:
        item = await session.get(IntakeItem, item_a)
        root_id = await enqueue_event(
            session,
            name=INTAKE_ITEM_RECEIVED,
            payload={
                "intakeItemId": str(item_a),
                "workspaceId": str(workspace_id),
                "intakeSourceId": str(item.intake_source_id),
                "providerName": item.provider_name,
                "receivedAt": item.received_at.isoformat(),
                "fingerprint": item.fingerprint,
                "externalId": item.external_id,
            },
            workspace_id=workspace_id,
        )
        await session.commit()

    # ---- Step 2-3: extract + classify (one call) ----
    claim_ids = await ClaimService(
        sm, extractor=_FakeExtractor(triples), classifier=_FakeClassifier()
    ).extract_claims_from_intake_item(
        intake_item_id=item_a,
        workspace_id=workspace_id,
        causation_event_id=str(root_id),
    )
    assert len(claim_ids) == 1
    claim_id = claim_ids[0]

    async with sm() as session:
        claim = await session.get(Claim, claim_id)
        assert claim.subject == subj_a
        assert claim.epistemic_type == "claim"  # classified
        extracted = await _event(session, CLAIM_EXTRACTED, claim_id=claim_id)
        typed = await _event(session, CLAIM_TYPED, claim_id=claim_id)
        assert extracted["causationId"] == str(root_id)
        assert typed["causationId"] == extracted["id"]

    # ---- Step 4: evidence collection (real FTS finds item_b) ----
    async with sm() as session:
        typed_ev = await _event(session, CLAIM_TYPED, claim_id=claim_id)
    ev_ids = await EvidenceService(sm, linker=_FakeLinker()).collect_evidence_for_claim(
        claim_id=claim_id,
        workspace_id=workspace_id,
        causation_event_id=typed_ev["id"],
    )
    assert len(ev_ids) == 1  # corroborated by item_b
    async with sm() as session:
        collected = await _event(session, EVIDENCE_COLLECTED, claim_id=claim_id)
        assert collected["causationId"] == typed_ev["id"]

    # ---- Step 5: verification ----
    await VerificationService(sm).verify_claim(
        claim_id=claim_id,
        workspace_id=workspace_id,
        causation_event_id=collected["id"],
    )
    async with sm() as session:
        verified = await _event(session, CLAIM_VERIFIED, claim_id=claim_id)
        assert verified["causationId"] == collected["id"]
        assert verified["payload"]["outcome"] == "verified"

    # ---- Step 6: composition ----
    obj_id = await IntelligenceService(sm).compose_for_item(
        intake_item_id=item_a,
        workspace_id=workspace_id,
        causation_event_id=verified["id"],
    )
    assert obj_id is not None
    async with sm() as session:
        obj = await session.get(IntelligenceObject, obj_id)
        normalized = await session.get(IntakeItemNormalized, item_a)
        assert obj.headline == normalized.subject  # headline from intake, not AI
        assert subj_a in obj.key_facts  # structured, keyed by claim subject
        assert obj.confidence_score is not None
        assert obj.verification_status == "verified"
        created = await _event(session, OBJECT_CREATED)
        assert created["causationId"] == verified["id"]

    research = ResearchService(sm)
    # ---- Step 7-9: workspace + add object + packet ----
    rws = await research.create_workspace(
        workspace_id=workspace_id,
        account_id=account.id,
        name="E2E desk",
        description=None,
    )
    await research.add_item(
        workspace_id=workspace_id,
        rws_id=rws.id,
        account_id=account.id,
        object_id=obj_id,
        note=None,
    )
    packet = await research.create_packet(
        workspace_id=workspace_id,
        rws_id=rws.id,
        name="E2E packet",
        object_ids=[obj_id],
    )

    # ---- Step 10: readiness ----
    readiness = await research.check_readiness(
        workspace_id=workspace_id, packet_id=packet.id
    )
    assert readiness.is_ready is True
    assert readiness.blockers == []

    # ---- Step 11: mark ready ----
    ready = await research.mark_ready(workspace_id=workspace_id, packet_id=packet.id)
    assert ready.status == "ready"

    # ---- Step 12 + final assertions ----
    async with sm() as session:
        # consumed_at stays NULL — Phase 5 owns it.
        assert ready.consumed_at is None
        packet_ready = await _event(session, PACKET_READY)
        assert packet_ready is not None
        assert packet_ready["payload"]["packetId"] == str(packet.id)

        # Phase 4 wrote no new intake rows (2 items ingested, 2 normalized).
        item_count = (
            await session.execute(
                select(func.count())
                .select_from(IntakeItem)
                .where(IntakeItem.workspace_id == workspace_id)
            )
        ).scalar_one()
        assert item_count == 2
        norm_count = (
            await session.execute(
                select(func.count()).select_from(IntakeItemNormalized).where(
                    IntakeItemNormalized.intake_item_id.in_([item_a, item_b])
                )
            )
        ).scalar_one()
        assert norm_count == 2
