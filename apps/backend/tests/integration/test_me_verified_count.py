"""Command Center VERIFIED stat (2026-07-11) — /v1/auth/me verification.verifiedCount.

The stat's real definition, pinned: intelligence objects (the per-item verdict
unit — claims carry NO verification status column) whose verification_status is
'verified' OR 'analyst_approved'. Approval REPLACES 'verified' (the review flow
flips the enum), so a definition of only-'verified' would decrement the stat
the moment an analyst approves an object — exactly one object per status below
proves both inclusion and every exclusion.
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db

ALL_STATUSES = (
    "verified",
    "analyst_approved",
    "analyst_rejected",
    "contested",
    "unverified",
)


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _seed_objects(session, *, ws_id, statuses) -> None:
    """One intake source + one (item, intelligence_object) per status."""
    from oryx.core.models import IntakeItem, IntakeSource, IntelligenceObject

    now = datetime.now(UTC)
    source = IntakeSource(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        kind="rss",
        name="feed",
        enabled=True,
        config={},
        origin_kind="custom",
        status="healthy",
    )
    session.add(source)
    await session.flush()
    for status in statuses:
        item = IntakeItem(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            intake_source_id=source.id,
            provider_name="rss",
            external_id=f"x-{uuid.uuid4().hex[:8]}",
            received_at=now,
            payload={},
            fingerprint=uuid.uuid4().hex,
        )
        session.add(item)
        await session.flush()
        session.add(
            IntelligenceObject(
                id=uuid.uuid4(),
                workspace_id=ws_id,
                intake_item_id=item.id,
                epistemic_type="fact",
                confidence_score=0.9,
                verification_status=status,
                claim_ids=[],
                conflict_ids=[],
                key_facts={},
                headline=f"Obj {status}",
                scoring_version=1,
            )
        )
    await session.flush()


async def _signup(client) -> tuple[dict, uuid.UUID]:
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": f"verified+{uuid.uuid4().hex[:8]}@oryx.test",
            "password": "StrongPass123",
            "displayName": "Verifier",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "iPhone",
            "devicePlatform": "ios",
        },
    )
    access = signup.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {access}"}
    me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
    return headers, uuid.UUID(me["workspace"]["id"])


@pytest.mark.asyncio
async def test_me_verified_count_counts_verified_and_analyst_approved_only(
    app, sm
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers, ws_id = await _signup(client)

        me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
        assert me["verification"]["verifiedCount"] == 0  # brand-new workspace

        async with sm() as session:
            await _seed_objects(session, ws_id=ws_id, statuses=ALL_STATUSES)
            await session.commit()

        me2 = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
        # verified + analyst_approved; analyst_rejected/contested/unverified excluded.
        assert me2["verification"]["verifiedCount"] == 2


@pytest.mark.asyncio
async def test_me_verified_count_is_workspace_scoped(app, sm) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        headers_a, ws_a = await _signup(client)
        _headers_b, ws_b = await _signup(client)

        async with sm() as session:
            # Workspace B accumulates verified objects; A gets exactly one.
            await _seed_objects(
                session, ws_id=ws_b, statuses=("verified", "verified", "analyst_approved")
            )
            await _seed_objects(session, ws_id=ws_a, statuses=("verified",))
            await session.commit()

        me_a = (await client.get("/v1/auth/me", headers=headers_a)).json()["data"]
        assert me_a["verification"]["verifiedCount"] == 1  # B's objects invisible to A
