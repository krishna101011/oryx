"""Smoke test — proves the contract loop is closed."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from oryx.main import app


@pytest.mark.asyncio
async def test_health_returns_envelope() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "oryx-backend"
    assert "requestId" in body["meta"]
    assert "serverTime" in body["meta"]


@pytest.mark.asyncio
async def test_unknown_route_returns_envelope_error() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_phase1_stub_router_still_mounts() -> None:
    # The stub smoke check tracks whichever service is still a Phase 1 ping
    # stub. It has migrated /users → /verification (Wave C) → /research
    # (Wave E reclaimed /research) → /content (Phase 5 Wave A made content real)
    # → /publishing (Phase 5 Wave D made publishing real, so it moves on to
    # /automation, the next still-stubbed service — Phase 6).
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/automation/ping")
    assert response.status_code == 200
    assert response.json()["data"] == {"service": "automation", "pong": True}
