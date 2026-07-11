"""Feature flag resolution order: account override > workspace override > default."""
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


@pytest.mark.asyncio
async def test_default_flags_returned_for_new_account(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"flags+{uuid.uuid4().hex[:6]}@x.test",
            "password": "StrongPass123", "displayName": "F",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        access = signup.json()["data"]["tokens"]["accessToken"]
        res = await client.get(
            "/v1/feature-flags", headers={"Authorization": f"Bearer {access}"}
        )
        flags = res.json()["data"]
        # Seeded defaults from migration 0001, as resolved in the dev test
        # environment (ENVIRONMENT=dev). resolver._DEV_DEFAULT_ON force-enables
        # the two built-screen flags in dev so they don't show "Coming soon";
        # genuinely-unbuilt flags stay at their migration default (off).
        assert flags["ff_settings"] is True
        assert flags["ff_dashboard"] is True
        assert flags["ff_activity"] is True
        assert flags["ff_mfa"] is False
        assert flags["ff_research"] is True  # dev default-on (migration default is False)
        assert flags["ff_content_drafts"] is True  # dev default-on (migration default is False)
        assert flags["ff_intake_gmail"] is False
        assert flags["ff_team_workspaces"] is False


@pytest.mark.asyncio
async def test_ff_intake_rss_enabled_by_default(app) -> None:
    """Migration 0023 flips ff_intake_rss's global default ON — Phase 3 shipped
    the whole RSS path the flag gates (provider, router validation, scheduler,
    dedupe, circuit breaker), and the flag itself gates only the client's
    "Add an RSS feed" card; the backend endpoints behind it were already live
    and capability-gated. Pins TRUE so a rebuilt seed can't silently regress
    Manage Sources back to an empty screen."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"flags+{uuid.uuid4().hex[:6]}@x.test",
            "password": "StrongPass123", "displayName": "F",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        access = signup.json()["data"]["tokens"]["accessToken"]
        res = await client.get(
            "/v1/feature-flags", headers={"Authorization": f"Bearer {access}"}
        )
        flags = res.json()["data"]
        assert flags["ff_intake_rss"] is True
