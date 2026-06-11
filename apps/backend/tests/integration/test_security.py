"""Security pass — rate limit, lockout, permission deny, feature gate."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = [pytest.mark.requires_db, pytest.mark.security]


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ANANT_TEST_DB"])
    from anant.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_rate_limit_blocks_repeated_signin_attempts(app) -> None:
    """A burst of bad signins from the same IP gets 429 after the threshold."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        body = {
            "email": "nobody@example.com", "password": "WrongPass123",
            "deviceId": "x", "deviceLabel": "x", "devicePlatform": "ios",
        }
        # First N attempts get 401; the (N+1)th gets 429.
        codes = []
        for _ in range(7):
            r = await client.post("/v1/auth/signin", json=body)
            codes.append(r.status_code)
        assert 429 in codes, f"expected rate limiting, got codes={codes}"


@pytest.mark.asyncio
async def test_lockout_triggers_after_threshold_failures(app) -> None:
    """10 wrong passwords on the same account → account locked."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = f"test+{uuid.uuid4().hex[:8]}@anant.test"
        await client.post("/v1/auth/signup", json={
            "email": email, "password": "StrongPass123", "displayName": "x",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        # 10 wrong attempts — interleave devices to stay clear of the IP rate limit
        # by tweaking X-Forwarded-For to spread bucket keys.
        for i in range(11):
            await client.post(
                "/v1/auth/signin",
                json={
                    "email": email, "password": "WrongPass" + str(i),
                    "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
                },
                headers={"X-Forwarded-For": f"10.0.0.{i + 1}"},
            )
        # Now the correct password should also be rejected because account is locked.
        res = await client.post(
            "/v1/auth/signin",
            json={
                "email": email, "password": "StrongPass123",
                "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
            },
            headers={"X-Forwarded-For": "10.0.0.99"},
        )
        assert res.json()["error"]["code"] == "AUTH_ACCOUNT_LOCKED"


@pytest.mark.asyncio
async def test_account_isolation_blocks_other_users(app) -> None:
    """A signed-in user cannot fetch another account by id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        a = await client.post("/v1/auth/signup", json={
            "email": f"a+{uuid.uuid4().hex[:6]}@x.test", "password": "StrongPass123",
            "displayName": "A", "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        a_data = a.json()["data"]
        other_id = a_data["account"]["id"]

        b = await client.post("/v1/auth/signup", json={
            "email": f"b+{uuid.uuid4().hex[:6]}@x.test", "password": "StrongPass123",
            "displayName": "B", "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        b_access = b.json()["data"]["tokens"]["accessToken"]

        res = await client.get(
            f"/v1/users/{other_id}",
            headers={"Authorization": f"Bearer {b_access}"},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_auth_required(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get("/v1/auth/me")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTH_REQUIRED"
