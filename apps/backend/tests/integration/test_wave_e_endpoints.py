"""HTTP-level tests for the Wave E surface: /auth/me counts, intelligence
reads, and the research workspace/packet endpoints (signup → owner token)."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _auth(client: AsyncClient) -> dict[str, str]:
    signup = await client.post(
        "/v1/auth/signup",
        json={
            "email": f"wavee+{uuid.uuid4().hex[:8]}@oryx.test",
            "password": "StrongPass123",
            "displayName": "Analyst",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "iPhone",
            "devicePlatform": "ios",
        },
    )
    access = signup.json()["data"]["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_me_includes_verification_and_research_counts(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        me = await c.get("/v1/auth/me", headers=headers)
        data = me.json()["data"]
        assert data["verification"] == {"pendingReviewCount": 0, "openConflictCount": 0}
        assert data["research"] == {"activeWorkspaceCount": 0, "readyPacketCount": 0}


@pytest.mark.asyncio
async def test_intelligence_objects_empty_and_404(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        lst = await c.get("/v1/intelligence/objects", headers=headers)
        assert lst.status_code == 200
        assert lst.json()["data"] == []

        missing = await c.get(
            f"/v1/intelligence/objects/{uuid.uuid4()}", headers=headers
        )
        assert missing.status_code == 404
        stale = await c.get(
            f"/v1/intelligence/objects/{uuid.uuid4()}/stale", headers=headers
        )
        assert stale.status_code == 404


@pytest.mark.asyncio
async def test_research_workspace_crud(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        created = await c.post(
            "/v1/research/workspaces",
            json={"name": "Macro desk", "description": "rates"},
            headers=headers,
        )
        assert created.status_code == 200
        rws_id = created.json()["data"]["id"]

        listed = await c.get("/v1/research/workspaces", headers=headers)
        assert any(w["id"] == rws_id for w in listed.json()["data"])

        detail = await c.get(f"/v1/research/workspaces/{rws_id}", headers=headers)
        assert detail.json()["data"]["itemCount"] == 0

        patched = await c.patch(
            f"/v1/research/workspaces/{rws_id}",
            json={"name": "Macro v2"},
            headers=headers,
        )
        assert patched.json()["data"]["name"] == "Macro v2"


@pytest.mark.asyncio
async def test_archived_workspace_drops_from_list(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        created = await c.post(
            "/v1/research/workspaces",
            json={"name": "Temp", "description": None},
            headers=headers,
        )
        rws_id = created.json()["data"]["id"]
        await c.patch(
            f"/v1/research/workspaces/{rws_id}",
            json={"status": "archived"},
            headers=headers,
        )
        listed = await c.get("/v1/research/workspaces", headers=headers)
        assert all(w["id"] != rws_id for w in listed.json()["data"])


@pytest.mark.asyncio
async def test_packet_lifecycle_empty_packet_ready(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        rws = await c.post(
            "/v1/research/workspaces",
            json={"name": "P-WS", "description": None},
            headers=headers,
        )
        rws_id = rws.json()["data"]["id"]
        packet = await c.post(
            "/v1/research/packets",
            json={
                "research_workspace_id": rws_id,
                "name": "Empty packet",
                "intelligence_object_ids": [],
            },
            headers=headers,
        )
        assert packet.status_code == 200
        pid = packet.json()["data"]["id"]
        assert packet.json()["data"]["status"] == "assembling"
        assert packet.json()["data"]["consumedAt"] is None

        readiness = await c.get(
            f"/v1/research/packets/{pid}/readiness", headers=headers
        )
        assert readiness.json()["data"]["isReady"] is True

        ready = await c.post(f"/v1/research/packets/{pid}/ready", headers=headers)
        assert ready.status_code == 200
        assert ready.json()["data"]["status"] == "ready"
        assert ready.json()["data"]["readyAt"] is not None
        assert ready.json()["data"]["consumedAt"] is None

        # And it now shows in the /me ready count.
        me = await c.get("/v1/auth/me", headers=headers)
        assert me.json()["data"]["research"]["readyPacketCount"] == 1


@pytest.mark.asyncio
async def test_packet_get_and_list_filter(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        rws = await c.post(
            "/v1/research/workspaces",
            json={"name": "L-WS", "description": None},
            headers=headers,
        )
        rws_id = rws.json()["data"]["id"]
        packet = await c.post(
            "/v1/research/packets",
            json={
                "research_workspace_id": rws_id,
                "name": "P",
                "intelligence_object_ids": [],
            },
            headers=headers,
        )
        pid = packet.json()["data"]["id"]

        got = await c.get(f"/v1/research/packets/{pid}", headers=headers)
        assert got.json()["data"]["id"] == pid

        assembling = await c.get(
            "/v1/research/packets?status=assembling", headers=headers
        )
        assert any(p["id"] == pid for p in assembling.json()["data"])

        missing = await c.get(
            f"/v1/research/packets/{uuid.uuid4()}", headers=headers
        )
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_acknowledge_conflict_endpoint(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        headers = await _auth(c)
        rws = await c.post(
            "/v1/research/workspaces",
            json={"name": "Ack-WS", "description": None},
            headers=headers,
        )
        rws_id = rws.json()["data"]["id"]
        packet = await c.post(
            "/v1/research/packets",
            json={
                "research_workspace_id": rws_id,
                "name": "P",
                "intelligence_object_ids": [],
            },
            headers=headers,
        )
        pid = packet.json()["data"]["id"]
        obj_id = str(uuid.uuid4())
        ack = await c.post(
            f"/v1/research/packets/{pid}/acknowledge-conflict",
            json={"intelligence_object_id": obj_id},
            headers=headers,
        )
        assert ack.status_code == 200
        got = await c.get(f"/v1/research/packets/{pid}", headers=headers)
        assert obj_id in got.json()["data"]["conflictAcknowledgedIds"]


@pytest.mark.asyncio
async def test_workspace_requires_auth(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        res = await c.get("/v1/research/workspaces")
        assert res.status_code == 401
