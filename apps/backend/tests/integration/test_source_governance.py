"""Source-governance conflict-count join (2026-07-22 wave).

Proves the real join the recon ran by hand against the live dev DB
(claims -> intake_items -> conflict_records) against a fully controlled,
seeded scenario — hand-verified counts, not the ambient dev data.

Runs only when ORYX_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> dict:
    signup = await client.post("/v1/auth/signup", json={
        "email": f"srcgov+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "SG",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {access}"}
    me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
    return {"headers": headers, "workspace_id": uuid.UUID(me["workspace"]["id"])}


async def _seed_two_source_conflict_scene(sm) -> dict:
    """Two intake sources (A, B) in one workspace, three claims apiece.

    Conflicts seeded:
      - conflict 1: claim A1 <-> claim B1 (crosses A and B — counts for BOTH)
      - conflict 2: claim A2 <-> claim A3 (both from A — counts ONCE for A,
        zero for B; also proves a same-source pair doesn't double-count)
      - conflict 3: claim B2 <-> claim B3 (both from B — counts ONCE for B)
      - an unrelated third source C with its own claim, in a conflict with
        neither A nor B, to prove the join doesn't leak across sources.

    Hand-verified expectation: source A -> 2 conflicts (1, 2);
    source B -> 2 conflicts (1, 3); source C -> 0.
    """
    from oryx.core.models import Account, ConflictRecord, IntakeSource, Workspace
    from oryx.services.claims.repository import ClaimsRepository
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"srcgov+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Source Governance WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()

        async def make_source(name: str) -> uuid.UUID:
            src = IntakeSource(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                kind="rss",
                name=name,
                enabled=True,
                config={},
                origin_kind="custom",
                status="healthy",
            )
            session.add(src)
            await session.flush()
            return src.id

        source_a = await make_source("Source A")
        source_b = await make_source("Source B")
        source_c = await make_source("Source C")

        svc = IntakeService(session)

        async def ingest(source_id: uuid.UUID, subject: str) -> uuid.UUID:
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source_id,
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

        repo = ClaimsRepository(session)

        async def make_claim(source_id: uuid.UUID, label: str) -> uuid.UUID:
            item_id = await ingest(source_id, label)
            cid = await repo.insert_claim(
                workspace_id=workspace.id,
                intake_item_id=item_id,
                text=f"{label} text.",
                subject="Subject",
                predicate="predicate",
                object_=label,
                extractor_version=1,
            )
            assert cid is not None
            return cid

        a1 = await make_claim(source_a, "A1")
        a2 = await make_claim(source_a, "A2")
        a3 = await make_claim(source_a, "A3")
        b1 = await make_claim(source_b, "B1")
        b2 = await make_claim(source_b, "B2")
        b3 = await make_claim(source_b, "B3")
        await make_claim(source_c, "C1")

        def add_conflict(claim_x: uuid.UUID, claim_y: uuid.UUID) -> None:
            session.add(
                ConflictRecord(
                    id=uuid.uuid4(),
                    workspace_id=workspace.id,
                    claim_a_id=min(claim_x, claim_y),
                    claim_b_id=max(claim_x, claim_y),
                    conflict_type="direct_contradiction",
                    severity=0.5,
                    status="open",
                )
            )

        add_conflict(a1, b1)  # crosses A and B
        add_conflict(a2, a3)  # entirely within A
        add_conflict(b2, b3)  # entirely within B
        await session.commit()

        return {"workspace": workspace.id, "a": source_a, "b": source_b, "c": source_c}


@pytest.mark.asyncio
async def test_conflict_count_matches_hand_verified_scenario(sm) -> None:
    from oryx.services.verification.repository import VerificationRepository

    ids = await _seed_two_source_conflict_scene(sm)

    async with sm() as session:
        repo = VerificationRepository(session)
        count_a = await repo.count_conflicts_for_source(
            workspace_id=ids["workspace"], source_id=ids["a"]
        )
        count_b = await repo.count_conflicts_for_source(
            workspace_id=ids["workspace"], source_id=ids["b"]
        )
        count_c = await repo.count_conflicts_for_source(
            workspace_id=ids["workspace"], source_id=ids["c"]
        )

    assert count_a == 2  # a1<->b1, a2<->a3
    assert count_b == 2  # a1<->b1, b2<->b3
    assert count_c == 0  # C's claim is in no conflict at all


@pytest.mark.asyncio
async def test_cross_source_conflict_is_not_double_counted_within_one_source(sm) -> None:
    """A single conflict between two DIFFERENT claims of the SAME source must
    count once, not twice — the join must count distinct conflict ids, not
    matching claim rows (a naive join without DISTINCT would double this)."""
    from oryx.core.models import Account, ConflictRecord, IntakeSource, Workspace
    from oryx.services.claims.repository import ClaimsRepository
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService
    from oryx.services.verification.repository import VerificationRepository

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"srcgov2+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Source Governance WS 2", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="rss",
            name="Solo Source",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()

        svc = IntakeService(session)
        repo = ClaimsRepository(session)

        async def make_claim(label: str) -> uuid.UUID:
            res = await svc.ingest_raw_item(
                workspace_id=workspace.id,
                intake_source_id=source.id,
                provider_name="rss",
                raw=RawItem(
                    external_id=f"i-{uuid.uuid4().hex[:8]}",
                    received_at=now,
                    sender="Wire",
                    subject=label,
                    body_text=f"{label} body.",
                    body_html=None,
                    links=[],
                    payload={},
                ),
            )
            assert res.intake_item_id is not None
            cid = await repo.insert_claim(
                workspace_id=workspace.id,
                intake_item_id=res.intake_item_id,
                text=f"{label} text.",
                subject="Subject",
                predicate="predicate",
                object_=label,
                extractor_version=1,
            )
            assert cid is not None
            return cid

        claim_x = await make_claim("X")
        claim_y = await make_claim("Y")
        session.add(
            ConflictRecord(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                claim_a_id=min(claim_x, claim_y),
                claim_b_id=max(claim_x, claim_y),
                conflict_type="direct_contradiction",
                severity=0.5,
                status="open",
            )
        )
        await session.commit()

        result = await VerificationRepository(session).count_conflicts_for_source(
            workspace_id=workspace.id, source_id=source.id
        )
        assert result == 1


@pytest.mark.asyncio
async def test_get_credibility_endpoint_computes_real_conflict_count(app, sm) -> None:
    """End-to-end: GET /verification/credibility/{source_id} returns the real
    conflictCount, and GET /verification/credibility (list) omits it entirely
    (None, never a fabricated 0) — the absent-not-zero contract."""
    from oryx.core.models import ConflictRecord, IntakeSource, SourceCredibilityRecord
    from oryx.services.claims.repository import ClaimsRepository
    from oryx.services.intake.providers.base import RawItem
    from oryx.services.intake.service import IntakeService

    now = datetime.now(UTC)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        workspace_id = ids["workspace_id"]

        async with sm() as session:
            source = IntakeSource(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                kind="rss",
                name="Endpoint Source",
                enabled=True,
                config={},
                origin_kind="custom",
                status="healthy",
            )
            session.add(source)
            await session.flush()

            svc = IntakeService(session)
            repo = ClaimsRepository(session)

            async def make_claim(label: str) -> uuid.UUID:
                res = await svc.ingest_raw_item(
                    workspace_id=workspace_id,
                    intake_source_id=source.id,
                    provider_name="rss",
                    raw=RawItem(
                        external_id=f"i-{uuid.uuid4().hex[:8]}",
                        received_at=now,
                        sender="Wire",
                        subject=label,
                        body_text=f"{label} body.",
                        body_html=None,
                        links=[],
                        payload={},
                    ),
                )
                assert res.intake_item_id is not None
                cid = await repo.insert_claim(
                    workspace_id=workspace_id,
                    intake_item_id=res.intake_item_id,
                    text=f"{label} text.",
                    subject="Subject",
                    predicate="predicate",
                    object_=label,
                    extractor_version=1,
                )
                assert cid is not None
                return cid

            claim_x = await make_claim("X")
            claim_y = await make_claim("Y")
            session.add(
                ConflictRecord(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    claim_a_id=min(claim_x, claim_y),
                    claim_b_id=max(claim_x, claim_y),
                    conflict_type="direct_contradiction",
                    severity=0.5,
                    status="open",
                )
            )
            session.add(
                SourceCredibilityRecord(
                    workspace_id=workspace_id,
                    source_id=source.id,
                    accuracy_rate=0.8,
                    verified_claim_count=1,
                    contested_claim_count=0,
                    total_claim_count=2,
                )
            )
            await session.commit()

        detail = await client.get(
            f"/v1/verification/credibility/{source.id}", headers=ids["headers"]
        )
        assert detail.status_code == 200
        body = detail.json()["data"]
        assert body["conflictCount"] == 1

        listing = await client.get(
            "/v1/verification/credibility", headers=ids["headers"]
        )
        assert listing.status_code == 200
        rows = [r for r in listing.json()["data"] if r["sourceId"] == str(source.id)]
        assert len(rows) == 1
        assert rows[0]["conflictCount"] is None
