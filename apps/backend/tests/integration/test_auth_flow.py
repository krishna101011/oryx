"""End-to-end signup → signin → refresh → signout flow.

Runs only when ORYX_TEST_DB points at a fresh Postgres (with migrations applied).
Use a disposable schema or a docker-compose-up'd test database.
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


def _u() -> str:
    return f"test+{uuid.uuid4().hex[:8]}@oryx.test"


@pytest.fixture
def app():
    # Import inside fixture so unit suite never touches engine init.
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient, email: str | None = None) -> dict:
    body = {
        "email": email or _u(),
        "password": "StrongPass123",
        "displayName": "Test User",
        "deviceId": str(uuid.uuid4()),
        "deviceLabel": "Pytest Device",
        "devicePlatform": "ios",
    }
    res = await client.post("/v1/auth/signup", json=body)
    assert res.status_code == 200, res.text
    return res.json()["data"]


@pytest.mark.asyncio
async def test_signup_creates_atomic_account_workspace_member(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        data = await _signup(client)
        assert "tokens" in data
        assert data["account"]["status"] == "active"
        assert data["account"]["emailVerified"] is False
        # The signed token implicitly carries a workspaceId; /workspaces/current
        # confirms membership exists.
        access = data["tokens"]["accessToken"]
        headers = {"Authorization": f"Bearer {access}"}
        ws = await client.get("/v1/workspaces/current", headers=headers)
        assert ws.status_code == 200
        assert ws.json()["data"]["role"] == "owner"


@pytest.mark.asyncio
async def test_signin_rejects_wrong_password(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        await _signup(client, email)
        res = await client.post("/v1/auth/signin", json={
            "email": email, "password": "WrongPass987",
            "deviceId": str(uuid.uuid4()), "deviceLabel": "x", "devicePlatform": "ios",
        })
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_rotates_and_old_token_is_invalid(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        # Refresh validates device_id against the session, so signup must
        # use the same device id the refreshes present.
        device_id = "stable-device"
        res = await client.post("/v1/auth/signup", json={
            "email": _u(), "password": "StrongPass123", "displayName": "Test User",
            "deviceId": device_id, "deviceLabel": "Pytest Device", "devicePlatform": "ios",
        })
        assert res.status_code == 200, res.text
        data = res.json()["data"]
        old_refresh = data["tokens"]["refreshToken"]
        # First refresh — mint new pair, old token revoked.
        r1 = await client.post("/v1/auth/refresh", json={
            "refreshToken": old_refresh, "deviceId": device_id,
        })
        assert r1.status_code == 200
        new_refresh = r1.json()["data"]["refreshToken"]
        assert new_refresh != old_refresh
        # Reusing the old refresh token must trigger chain revocation.
        r2 = await client.post("/v1/auth/refresh", json={
            "refreshToken": old_refresh, "deviceId": device_id,
        })
        assert r2.status_code == 401
        assert r2.json()["error"]["code"] == "AUTH_REFRESH_REUSE_DETECTED"
        # And the previously-valid NEW refresh is also dead (chain revoked).
        r3 = await client.post("/v1/auth/refresh", json={
            "refreshToken": new_refresh, "deviceId": device_id,
        })
        assert r3.status_code == 401


@pytest.mark.asyncio
async def test_email_taken_rejected(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        await _signup(client, email)
        res = await client.post("/v1/auth/signup", json={
            "email": email, "password": "StrongPass123", "displayName": "Dup",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "AUTH_EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_weak_password_rejected(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.post("/v1/auth/signup", json={
            "email": _u(), "password": "short", "displayName": "x",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "AUTH_PASSWORD_WEAK"


# --- Web dual-auth: httpOnly session cookie -------------------------------

@pytest.mark.asyncio
async def test_signup_sets_session_cookie(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.post("/v1/auth/signup", json={
            "email": _u(), "password": "StrongPass123", "displayName": "Web User",
            "deviceId": str(uuid.uuid4()), "deviceLabel": "web", "devicePlatform": "web",
        })
        assert res.status_code == 200, res.text
        # Cookie present, httpOnly, and carries the access token (additive — body still has it).
        assert "oryx_session" in res.cookies
        set_cookie = res.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()
        # dev environment → no Secure attribute so it works over http://localhost.
        assert "secure" not in set_cookie.lower()
        assert res.cookies["oryx_session"] == res.json()["data"]["tokens"]["accessToken"]


@pytest.mark.asyncio
async def test_me_authenticates_via_cookie_without_bearer(app) -> None:
    """The page-reload scenario: no Authorization header, cookie carries the session."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": _u(), "password": "StrongPass123", "displayName": "Web User",
            "deviceId": str(uuid.uuid4()), "deviceLabel": "web", "devicePlatform": "web",
        })
        assert signup.status_code == 200
        # The AsyncClient cookie jar now holds oryx_session — send NO bearer header.
        me = await client.get("/v1/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["data"]["account"]["email"]


@pytest.mark.asyncio
async def test_signout_clears_cookie_and_blocks_subsequent_request(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        await client.post("/v1/auth/signup", json={
            "email": _u(), "password": "StrongPass123", "displayName": "Web User",
            "deviceId": str(uuid.uuid4()), "deviceLabel": "web", "devicePlatform": "web",
        })
        # Authenticated via cookie before signout.
        assert (await client.get("/v1/auth/me")).status_code == 200
        out = await client.post("/v1/auth/signout")
        assert out.status_code == 200
        # Cookie is expired/removed from the jar → next protected call is 401.
        client.cookies.delete("oryx_session")
        me = await client.get("/v1/auth/me")
        assert me.status_code == 401
