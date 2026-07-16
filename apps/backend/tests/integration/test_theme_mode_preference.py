"""Theming Phase A — themeMode persists through the REAL Preferences object.

The client's light/dark switch is account-synced: it PATCHes /v1/preferences
and hydrates back through /v1/auth/me. These tests round-trip that path
against the real DB (no mocks), including the migration 0025 default.
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
        "email": f"theme+{uuid.uuid4().hex[:8]}@oryx.test",
        "password": "StrongPass123", "displayName": "Theme Tester",
        "deviceId": str(uuid.uuid4()), "deviceLabel": "web", "devicePlatform": "web",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_theme_mode_defaults_to_dark_on_signup(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        me = await client.get("/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["data"]["preferences"]["themeMode"] == "dark"
        prefs = await client.get("/v1/preferences", headers=headers)
        assert prefs.json()["data"]["themeMode"] == "dark"


@pytest.mark.asyncio
async def test_theme_mode_round_trips_through_preferences_patch_and_me(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)

        patched = await client.patch(
            "/v1/preferences", json={"themeMode": "light"}, headers=headers,
        )
        assert patched.status_code == 200
        assert patched.json()["data"]["themeMode"] == "light"

        # The bootstrap envelope — the client's hydration source — agrees.
        me = await client.get("/v1/auth/me", headers=headers)
        assert me.json()["data"]["preferences"]["themeMode"] == "light"

        # And back to dark, proving a real toggle, not a one-way write.
        back = await client.patch(
            "/v1/preferences", json={"themeMode": "dark"}, headers=headers,
        )
        assert back.json()["data"]["themeMode"] == "dark"
        me2 = await client.get("/v1/auth/me", headers=headers)
        assert me2.json()["data"]["preferences"]["themeMode"] == "dark"


@pytest.mark.asyncio
async def test_theme_mode_rejects_unknown_values(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        bad = await client.patch(
            "/v1/preferences", json={"themeMode": "sepia"}, headers=headers,
        )
        assert bad.status_code == 422


@pytest.mark.asyncio
async def test_theme_mode_patch_leaves_other_preferences_untouched(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        before = (await client.get("/v1/preferences", headers=headers)).json()["data"]
        await client.patch("/v1/preferences", json={"themeMode": "light"}, headers=headers)
        after = (await client.get("/v1/preferences", headers=headers)).json()["data"]
        assert after["themeMode"] == "light"
        for key in ("focus", "contentStyle", "verificationStrictness",
                    "notificationFrequency", "customTopics"):
            assert after[key] == before[key], f"{key} must not change"
