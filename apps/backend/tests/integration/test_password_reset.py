"""Password reset — the real email path (rewired from the permanent
LogOnlyEmailProvider stub) and the token-based /password/reset endpoint that
previously returned 501.

The forgot-password flow resolves its provider through the SAME
EMAIL_PROVIDER-gated factory alert delivery uses (get_email_provider,
monkeypatched here at the auth router seam exactly like
test_email_delivery.py patches it at the dispatcher seam) — there is no
auth-specific email config surface.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field

import pytest
from httpx import ASGITransport, AsyncClient

import oryx.services.auth.router as auth_router
from oryx.services.auth.providers.email.base import EmailMessage, ProviderResult

pytestmark = pytest.mark.requires_db


def _u() -> str:
    return f"test+{uuid.uuid4().hex[:8]}@oryx.test"


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


@dataclass
class FakeEmailProvider:
    name: str = "fake"
    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> ProviderResult:
        self.sent.append(message)
        return ProviderResult(ok=True, provider=self.name, message_id="fake-1")


@pytest.fixture
def fake_email(monkeypatch) -> FakeEmailProvider:
    provider = FakeEmailProvider()
    # The router resolves the provider per request via the EMAIL_PROVIDER
    # factory; patch that seam, same pattern as the dispatcher tests.
    monkeypatch.setattr(auth_router, "get_email_provider", lambda: provider)
    return provider


async def _signup(client: AsyncClient, email: str, device_id: str = "reset-dev") -> dict:
    res = await client.post("/v1/auth/signup", json={
        "email": email, "password": "StrongPass123", "displayName": "Reset User",
        "deviceId": device_id, "deviceLabel": "Pytest Device", "devicePlatform": "ios",
    })
    assert res.status_code == 200, res.text
    return res.json()["data"]


async def _forgot_and_grab_token(
    client: AsyncClient, fake_email: FakeEmailProvider, email: str
) -> str:
    res = await client.post("/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200
    assert len(fake_email.sent) == 1
    return fake_email.sent[-1].variables["reset_token"]


@pytest.mark.asyncio
async def test_forgot_password_sends_reset_email_via_provider_factory(
    app, fake_email
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        await _signup(client, email)
        res = await client.post("/v1/auth/password/forgot", json={"email": email})
        assert res.status_code == 200
        assert len(fake_email.sent) == 1
        msg = fake_email.sent[0]
        assert msg.to == email
        assert msg.template == "password_reset"
        assert msg.variables["reset_token"]  # a real signed token, not an id
        assert "account_id" not in msg.variables  # internal ids stay internal


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_is_private_and_sends_nothing(
    app, fake_email
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.post(
            "/v1/auth/password/forgot", json={"email": "nobody@oryx.test"}
        )
        # Same 200 as the known-email case — existence stays unguessable.
        assert res.status_code == 200
        assert res.json()["data"] == {"ok": True}
        assert fake_email.sent == []


@pytest.mark.asyncio
async def test_reset_password_round_trip_endpoint_no_longer_501(
    app, fake_email
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        await _signup(client, email)
        token = await _forgot_and_grab_token(client, fake_email, email)

        res = await client.post("/v1/auth/password/reset", json={
            "token": token, "newPassword": "FreshPass456",
        })
        assert res.status_code != 501  # the Phase 2 stub is gone
        assert res.status_code == 200, res.text
        assert res.json()["data"] == {"ok": True}

        # New password signs in; the old one is dead.
        ok = await client.post("/v1/auth/signin", json={
            "email": email, "password": "FreshPass456",
            "deviceId": "d2", "deviceLabel": "x", "devicePlatform": "ios",
        })
        assert ok.status_code == 200, ok.text
        stale = await client.post("/v1/auth/signin", json={
            "email": email, "password": "StrongPass123",
            "deviceId": "d3", "deviceLabel": "x", "devicePlatform": "ios",
        })
        assert stale.status_code == 401


@pytest.mark.asyncio
async def test_reset_token_is_single_use(app, fake_email) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        await _signup(client, email)
        token = await _forgot_and_grab_token(client, fake_email, email)
        first = await client.post("/v1/auth/password/reset", json={
            "token": token, "newPassword": "FreshPass456",
        })
        assert first.status_code == 200
        # The password changed, so the token's pwd fingerprint no longer
        # matches — replaying it must fail.
        replay = await client.post("/v1/auth/password/reset", json={
            "token": token, "newPassword": "EvilPass789",
        })
        assert replay.status_code == 401
        assert replay.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_reset_rejects_garbage_and_access_tokens(app, fake_email) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        data = await _signup(client, email)
        garbage = await client.post("/v1/auth/password/reset", json={
            "token": "not-a-token", "newPassword": "FreshPass456",
        })
        assert garbage.status_code == 401
        # A real, valid ACCESS token must not work as a reset token (typ check).
        crossed = await client.post("/v1/auth/password/reset", json={
            "token": data["tokens"]["accessToken"], "newPassword": "FreshPass456",
        })
        assert crossed.status_code == 401


@pytest.mark.asyncio
async def test_reset_revokes_existing_sessions(app, fake_email) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        email = _u()
        device_id = "reset-dev"
        data = await _signup(client, email, device_id=device_id)
        refresh = data["tokens"]["refreshToken"]
        token = await _forgot_and_grab_token(client, fake_email, email)
        res = await client.post("/v1/auth/password/reset", json={
            "token": token, "newPassword": "FreshPass456",
        })
        assert res.status_code == 200
        # The pre-reset session chain is revoked — its refresh token is dead.
        stale = await client.post("/v1/auth/refresh", json={
            "refreshToken": refresh, "deviceId": device_id,
        })
        assert stale.status_code == 401
