"""/v1/auth/me returns the full bootstrap envelope in one round-trip."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ANANT_TEST_DB"])
    from anant.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_me_envelope_contains_every_section(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"test+{uuid.uuid4().hex[:8]}@anant.test",
            "password": "StrongPass123", "displayName": "Me",
            "deviceId": str(uuid.uuid4()), "deviceLabel": "iPhone", "devicePlatform": "ios",
        })
        access = signup.json()["data"]["tokens"]["accessToken"]
        me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        data = me.json()["data"]
        # Every section present:
        for key in ("account", "profile", "workspace", "preferences",
                    "activity", "flags", "onboarding", "serverTime", "build"):
            assert key in data, f"missing {key}"
        # Defaults from the migration seeds:
        assert data["flags"]["ff_settings"] is True
        assert data["flags"]["ff_intake_gmail"] is False
        # Onboarding state is freshly set to incomplete after signup.
        assert data["onboarding"]["state"] == "incomplete"
        assert data["onboarding"]["nextStep"] in {
            "welcome", "focus_sources", "notifications_permissions", "style_strictness",
        }


@pytest.mark.asyncio
async def test_mfa_endpoints_return_501_cleanly(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"test+{uuid.uuid4().hex[:8]}@anant.test",
            "password": "StrongPass123", "displayName": "Me",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        access = signup.json()["data"]["tokens"]["accessToken"]
        headers = {"Authorization": f"Bearer {access}"}
        for path in ("/v1/auth/mfa/setup", "/v1/auth/mfa/disable"):
            res = await client.post(path, headers=headers)
            assert res.status_code == 501
            assert res.json()["error"]["code"] == "NOT_IMPLEMENTED"
        verify = await client.post(
            "/v1/auth/mfa/verify", json={"code": "000000"}, headers=headers,
        )
        assert verify.status_code == 501
