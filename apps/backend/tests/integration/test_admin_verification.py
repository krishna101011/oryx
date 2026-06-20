"""Admin re-run surface (Wave F): reextract / reverify / rescore / budget,
plus the platform-admin gate."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


def _svc(sm):
    from oryx.services.admin.service import AdminVerificationService

    return AdminVerificationService(sm)


async def _seed(sm, *, with_items=0, with_claims=0, with_object=False) -> dict:
    from oryx.core.models import (
        Account,
        IntakeSource,
        IntelligenceObject,
        VerificationRun,
        Workspace,
    )
    from oryx.services.claims.repository import ClaimsRepository
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"adm+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(id=uuid.uuid4(), name="Admin WS", owner_account_id=account.id)
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
        item_ids = []
        for _ in range(max(with_items, with_claims, 1 if with_object else 0)):
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                provider_name="rss",
                raw=RawItem(
                    external_id=f"i-{uuid.uuid4().hex[:8]}",
                    received_at=now,
                    sender="Wire",
                    subject=f"Item {uuid.uuid4().hex[:5]}",
                    body_text="Acme raised funds.",
                    body_html=None,
                    links=[],
                    payload={},
                ),
            )
            item_ids.append(res.intake_item_id)

        repo = ClaimsRepository(session)
        claim_ids = []
        for i in range(with_claims):
            cid = await repo.insert_claim(
                workspace_id=workspace.id,
                intake_item_id=item_ids[i],
                text=f"Acme fact {i}",
                subject=f"Acme {i}",
                predicate="raised",
                object_="funds",
                extractor_version=1,
            )
            await repo.set_epistemic_type(
                claim_id=cid, epistemic_type="claim",
                classifier_version=1, requires_analyst_review=False,
            )
            claim_ids.append(cid)
            session.add(
                VerificationRun(
                    id=uuid.uuid4(), claim_id=cid, status="complete",
                    outcome="verified", confidence_score=0.6,
                    engine_version=1, scoring_version=1,
                    started_at=now, completed_at=now,
                )
            )

        object_id = None
        if with_object:
            obj = IntelligenceObject(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                intake_item_id=item_ids[0],
                epistemic_type="claim",
                confidence_score=0.6,
                verification_status="verified",
                claim_ids=claim_ids,
                conflict_ids=[],
                key_facts={},
                headline="Obj",
                scoring_version=1,
            )
            session.add(obj)
            object_id = obj.id

        await session.commit()
        return {
            "account": account.id,
            "workspace": workspace.id,
            "items": item_ids,
            "claims": claim_ids,
            "object": object_id,
        }


@pytest.mark.asyncio
async def test_budget_default_when_no_row(sm) -> None:
    ids = await _seed(sm)
    data = await _svc(sm).budget(workspace_id=ids["workspace"])
    assert data["tokens_used"] == 0
    assert data["budget_limit"] == 100000
    assert data["utilization"] == 0.0


@pytest.mark.asyncio
async def test_budget_reflects_usage(sm) -> None:
    from oryx.core.models import WorkspaceAIBudget

    ids = await _seed(sm)
    async with sm() as session:
        session.add(
            WorkspaceAIBudget(
                workspace_id=ids["workspace"],
                budget_date=date.today(),
                tokens_used=25000,
                budget_limit=100000,
            )
        )
        await session.commit()
    data = await _svc(sm).budget(workspace_id=ids["workspace"])
    assert data["tokens_used"] == 25000
    assert data["utilization"] == pytest.approx(0.25)


async def _intake_event_count(sm, workspace_id) -> int:
    from oryx.core.models import OutboxEvent
    from oryx.services.intake.events_constants import INTAKE_ITEM_RECEIVED

    async with sm() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(
                        OutboxEvent.workspace_id == workspace_id,
                        OutboxEvent.event_name == INTAKE_ITEM_RECEIVED,
                    )
                )
            ).scalar_one()
        )


@pytest.mark.asyncio
async def test_reextract_dry_run_counts_only(sm) -> None:
    ids = await _seed(sm, with_items=2)
    before = await _intake_event_count(sm, ids["workspace"])  # ingest emitted some
    count = await _svc(sm).reextract(
        workspace_id=ids["workspace"],
        intake_item_ids=None,
        dry_run=True,
        account_id=ids["account"],
    )
    assert count == 2
    after = await _intake_event_count(sm, ids["workspace"])
    assert after == before  # dry run takes no action


@pytest.mark.asyncio
async def test_reextract_enqueues_events(sm) -> None:
    ids = await _seed(sm, with_items=2)
    before = await _intake_event_count(sm, ids["workspace"])
    queued = await _svc(sm).reextract(
        workspace_id=ids["workspace"],
        intake_item_ids=None,
        dry_run=False,
        account_id=ids["account"],
    )
    assert queued == 2
    after = await _intake_event_count(sm, ids["workspace"])
    assert after - before == 2  # one synthetic re-extract event per item


@pytest.mark.asyncio
async def test_reverify_inserts_pending_and_queues(sm) -> None:
    from oryx.core.models import OutboxEvent, VerificationAuditLog, VerificationRun
    from oryx.services.evidence.events.constants import EVIDENCE_COLLECTED

    ids = await _seed(sm, with_claims=2)
    queued = await _svc(sm).reverify(
        workspace_id=ids["workspace"],
        claim_ids=ids["claims"],
        reason="engine v2 backfill",
        account_id=ids["account"],
    )
    assert queued == 2
    async with sm() as session:
        pending = (
            await session.execute(
                select(VerificationRun).where(
                    VerificationRun.claim_id.in_(ids["claims"]),
                    VerificationRun.status == "pending",
                )
            )
        ).scalars().all()
        assert len(pending) == 2
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == EVIDENCE_COLLECTED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(events) == 2
        audit = (
            await session.execute(
                select(VerificationAuditLog).where(
                    VerificationAuditLog.event == "reverify_requested",
                    VerificationAuditLog.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert len(audit) == 2
        assert audit[0].data["reason"] == "engine v2 backfill"


@pytest.mark.asyncio
async def test_rescore_updates_runs_and_objects(sm) -> None:
    from oryx.core.models import IntelligenceObject, OutboxEvent
    from oryx.services.intelligence.events.constants import OBJECT_UPDATED

    ids = await _seed(sm, with_claims=1, with_object=True)
    updated_runs, updated_objects = await _svc(sm).rescore(
        workspace_id=ids["workspace"]
    )
    assert updated_runs >= 1
    assert updated_objects == 1
    async with sm() as session:
        obj = await session.get(IntelligenceObject, ids["object"])
        assert obj.scoring_version == 1  # CURRENT_SCORING_VERSION
        events = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.event_name == OBJECT_UPDATED,
                    OutboxEvent.workspace_id == ids["workspace"],
                )
            )
        ).scalars().all()
        assert any(
            e.event["payload"].get("changeType") == "score_update" for e in events
        )


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


@pytest.mark.asyncio
async def test_admin_gate_rejects_non_platform_admin(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        signup = await c.post(
            "/v1/auth/signup",
            json={
                "email": f"plain+{uuid.uuid4().hex[:8]}@oryx.test",
                "password": "StrongPass123",
                "displayName": "Plain",
                "deviceId": str(uuid.uuid4()),
                "deviceLabel": "iPhone",
                "devicePlatform": "ios",
            },
        )
        access = signup.json()["data"]["tokens"]["accessToken"]
        res = await c.post(
            "/v1/admin/verification/reextract",
            json={"workspace_id": str(uuid.uuid4()), "dry_run": True},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert res.status_code == 403
