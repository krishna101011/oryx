"""Onboarding step durability across device switches."""
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
async def test_onboarding_state_persists_across_signins(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = f"test+{uuid.uuid4().hex[:8]}@oryx.test"
        # 1. signup (device A) -> partial onboarding (welcome + focus_sources)
        s1 = await client.post("/v1/auth/signup", json={
            "email": email, "password": "StrongPass123", "displayName": "X",
            "deviceId": "device-A", "deviceLabel": "iPhone A", "devicePlatform": "ios",
        })
        access_a = s1.json()["data"]["tokens"]["accessToken"]
        h_a = {"Authorization": f"Bearer {access_a}"}
        await client.post("/v1/onboarding/step", json={"step": "welcome"}, headers=h_a)
        await client.post("/v1/onboarding/step", json={
            "step": "focus_sources", "focus": "crypto",
        }, headers=h_a)
        # 2. signin from a fresh device B
        s2 = await client.post("/v1/auth/signin", json={
            "email": email, "password": "StrongPass123",
            "deviceId": "device-B", "deviceLabel": "iPad B", "devicePlatform": "ios",
        })
        access_b = s2.json()["data"]["tokens"]["accessToken"]
        h_b = {"Authorization": f"Bearer {access_b}"}
        me = await client.get("/v1/auth/me", headers=h_b)
        # The next step is notifications_permissions — the wizard resumes there.
        assert me.json()["data"]["onboarding"]["nextStep"] == "notifications_permissions"
        # 3. complete the wizard from device B
        await client.post("/v1/onboarding/step", json={
            "step": "notifications_permissions", "notificationFrequency": "daily",
        }, headers=h_b)
        await client.post("/v1/onboarding/step", json={
            "step": "style_strictness", "contentStyle": "balanced",
            "verificationStrictness": "strict",
        }, headers=h_b)
        final = await client.get("/v1/auth/me", headers=h_b)
        assert final.json()["data"]["onboarding"]["state"] == "complete"
        assert final.json()["data"]["preferences"]["verificationStrictness"] == "strict"
