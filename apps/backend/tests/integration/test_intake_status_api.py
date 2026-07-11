"""GET /v1/intake/status — the Command Center SOURCES stat's data contract.

The mobile dashboard renders this endpoint's `total` (2026-07-11 fix: the stat
was a hardcoded Phase 1 zero). These tests pin that a seeded source really
counts, and that the count is workspace-scoped.
"""
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


async def _signup(client: AsyncClient) -> dict[str, str]:
    signup = await client.post("/v1/auth/signup", json={
        "email": f"intakestatus+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "S",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_intake_status_counts_seeded_source_not_zero(app) -> None:
    """Command Center shows the real source count against a seeded source:
    a fresh workspace reports 0, and creating one RSS source over the real
    API moves total (and byHealth.healthy) to 1."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)

        before = (await client.get("/v1/intake/status", headers=headers)).json()["data"]
        assert before == {
            "total": 0,
            "byHealth": {"healthy": 0, "degraded": 0, "auth_required": 0, "disabled": 0},
        }

        created = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "Seeded feed",
            "kind": "rss",
            "origin_kind": "custom",
            "config": {"feed_url": "https://example.test/feed.xml"},
        })
        assert created.status_code == 200, created.text

        after = (await client.get("/v1/intake/status", headers=headers)).json()["data"]
        assert after["total"] == 1
        assert after["byHealth"]["healthy"] == 1


@pytest.mark.asyncio
async def test_intake_status_is_workspace_scoped(app) -> None:
    """Another account's sources must not leak into my count."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        theirs = await _signup(client)
        created = await client.post("/v1/intake/sources", headers=theirs, json={
            "name": "Their feed",
            "kind": "rss",
            "origin_kind": "custom",
            "config": {"feed_url": "https://example.test/theirs.xml"},
        })
        assert created.status_code == 200, created.text

        mine = await _signup(client)
        status = (await client.get("/v1/intake/status", headers=mine)).json()["data"]
        assert status["total"] == 0
