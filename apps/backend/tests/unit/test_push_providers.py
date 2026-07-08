"""Phase 6 Wave C — FCM/APNs providers + the PUSH_PROVIDER switch (unit, no DB).

Same standard as Phase 5 Wave D's social channels (test_publishing_channels.py):
real, complete implementations exercised through a faked httpx layer — the JWT
signing paths run against real ephemeral keys generated here, so no Firebase or
Apple account is needed to prove correctness. Also covers the error taxonomy
(401/403 → AUTH, 429 → RATE_LIMITED, 400/404/410 → PERMANENT, 5xx → TRANSIENT)
and that an unconfigured provider degrades to an AUTH failure result instead of
raising.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from oryx.services.activity.providers.push.base import (
    ProviderErrorKind,
    PushMessage,
)


def _pem(private_key) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _fake_service_account() -> dict:
    # A structurally real Firebase service-account payload with an ephemeral
    # RSA key, so the RS256 assertion in _access_token really signs.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {
        "project_id": "oryx-test",
        "client_email": "push@oryx-test.iam.gserviceaccount.com",
        "private_key": _pem(key),
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def _apns_key_pem() -> str:
    # APNs auth keys are ECDSA P-256 (.p8) — generate a real one.
    return _pem(ec.generate_private_key(ec.SECP256R1()))


def _message() -> PushMessage:
    return PushMessage(
        token="device-token-1",
        title="Conflict detected",
        body="",
        data={"category": "verification", "event_id": "e-1"},
    )


@pytest.fixture(autouse=True)
def _clear_token_caches():
    from oryx.services.activity.providers.push import apns, fcm

    fcm._token_cache.clear()
    apns._token_cache.clear()
    yield
    fcm._token_cache.clear()
    apns._token_cache.clear()


# --------------------------------------------------------------------------- #
# FCM
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_fcm_send_via_fake_http() -> None:
    from oryx.services.activity.providers.push.fcm import FCMProvider

    seen: dict = {}

    async def fake_post(self, url, **kw):
        if "oauth2" in url:
            seen["assertion"] = kw["data"]["assertion"]
            return httpx.Response(
                200,
                json={"access_token": "at-123", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )
        seen["url"] = url
        seen["json"] = kw["json"]
        seen["auth"] = kw["headers"]["Authorization"]
        return httpx.Response(
            200,
            json={"name": "projects/oryx-test/messages/msg-1"},
            request=httpx.Request("POST", url),
        )

    provider = FCMProvider(_fake_service_account())
    with patch("httpx.AsyncClient.post", fake_post):
        result = await provider.send(_message())

    assert result.ok is True
    assert result.provider == "fcm"
    assert result.message_id == "projects/oryx-test/messages/msg-1"
    # The real wire shape: v1 endpoint, bearer token, string-valued data.
    assert seen["url"].endswith("/v1/projects/oryx-test/messages:send")
    assert seen["auth"] == "Bearer at-123"
    assert seen["json"]["message"]["token"] == "device-token-1"
    assert seen["json"]["message"]["notification"] == {"title": "Conflict detected"}
    assert all(isinstance(v, str) for v in seen["json"]["message"]["data"].values())
    # The OAuth assertion is a real three-segment JWS.
    assert len(seen["assertion"].split(".")) == 3


@pytest.mark.asyncio
async def test_fcm_unregistered_token_is_permanent() -> None:
    from oryx.services.activity.providers.push.fcm import FCMProvider

    async def fake_post(self, url, **kw):
        if "oauth2" in url:
            return httpx.Response(
                200, json={"access_token": "at", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(
            404, json={"error": {"status": "UNREGISTERED"}},
            request=httpx.Request("POST", url),
        )

    provider = FCMProvider(_fake_service_account())
    with patch("httpx.AsyncClient.post", fake_post):
        result = await provider.send(_message())
    assert result.ok is False
    assert result.error_kind is ProviderErrorKind.PERMANENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ProviderErrorKind.AUTH),
        (403, ProviderErrorKind.AUTH),
        (429, ProviderErrorKind.RATE_LIMITED),
        (503, ProviderErrorKind.TRANSIENT),
    ],
)
async def test_fcm_error_taxonomy(status: int, expected: ProviderErrorKind) -> None:
    from oryx.services.activity.providers.push.fcm import FCMProvider

    async def fake_post(self, url, **kw):
        if "oauth2" in url:
            return httpx.Response(
                200, json={"access_token": "at", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(status, text="err", request=httpx.Request("POST", url))

    provider = FCMProvider(_fake_service_account())
    with patch("httpx.AsyncClient.post", fake_post):
        result = await provider.send(_message())
    assert result.ok is False
    assert result.error_kind is expected


@pytest.mark.asyncio
async def test_fcm_unconfigured_degrades_to_auth_result() -> None:
    from oryx.services.activity.providers.push.fcm import FCMProvider

    result = await FCMProvider(None).send(_message())
    assert result.ok is False
    assert result.error_kind is ProviderErrorKind.AUTH
    assert "FCM_SERVICE_ACCOUNT_FILE" in (result.error_message or "")


@pytest.mark.asyncio
async def test_fcm_access_token_is_cached_across_sends() -> None:
    from oryx.services.activity.providers.push.fcm import FCMProvider

    calls = {"token": 0}

    async def fake_post(self, url, **kw):
        if "oauth2" in url:
            calls["token"] += 1
            return httpx.Response(
                200, json={"access_token": "at", "expires_in": 3600},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(
            200, json={"name": "m"}, request=httpx.Request("POST", url)
        )

    provider = FCMProvider(_fake_service_account())
    with patch("httpx.AsyncClient.post", fake_post):
        await provider.send(_message())
        await provider.send(_message())
    assert calls["token"] == 1  # second send reused the cached token


# --------------------------------------------------------------------------- #
# APNs
# --------------------------------------------------------------------------- #
def _apns_provider(**overrides):
    from oryx.services.activity.providers.push.apns import APNsProvider

    kwargs = {
        "key_pem": _apns_key_pem(),
        "key_id": "KEYID12345",
        "team_id": "TEAMID9999",
        "topic": "com.oryx.app",
        "use_sandbox": True,
    }
    kwargs.update(overrides)
    return APNsProvider(**kwargs)


@pytest.mark.asyncio
async def test_apns_send_via_fake_http() -> None:
    seen: dict = {}

    async def fake_post(self, url, **kw):
        seen["url"] = url
        seen["headers"] = kw["headers"]
        seen["json"] = kw["json"]
        return httpx.Response(
            200,
            headers={"apns-id": "apns-msg-1"},
            request=httpx.Request("POST", url),
        )

    provider = _apns_provider()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await provider.send(_message())

    assert result.ok is True
    assert result.provider == "apns"
    assert result.message_id == "apns-msg-1"
    # Real wire shape: sandbox host, /3/device/{token}, topic + push-type
    # headers, ES256 bearer JWT, alert payload beside custom data.
    assert seen["url"] == "https://api.sandbox.push.apple.com/3/device/device-token-1"
    assert seen["headers"]["apns-topic"] == "com.oryx.app"
    assert seen["headers"]["apns-push-type"] == "alert"
    assert seen["headers"]["authorization"].startswith("bearer ")
    assert len(seen["headers"]["authorization"].removeprefix("bearer ").split(".")) == 3
    assert seen["json"]["aps"]["alert"] == {"title": "Conflict detected"}
    assert seen["json"]["category"] == "verification"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, ProviderErrorKind.PERMANENT),  # BadDeviceToken
        (403, ProviderErrorKind.AUTH),
        (410, ProviderErrorKind.PERMANENT),  # Unregistered
        (429, ProviderErrorKind.RATE_LIMITED),
        (500, ProviderErrorKind.TRANSIENT),
    ],
)
async def test_apns_error_taxonomy(status: int, expected: ProviderErrorKind) -> None:
    async def fake_post(self, url, **kw):
        return httpx.Response(
            status, json={"reason": "SomeReason"}, request=httpx.Request("POST", url)
        )

    provider = _apns_provider()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await provider.send(_message())
    assert result.ok is False
    assert result.error_kind is expected


@pytest.mark.asyncio
async def test_apns_unconfigured_degrades_to_auth_result() -> None:
    provider = _apns_provider(key_pem=None, key_id=None, team_id=None)
    result = await provider.send(_message())
    assert result.ok is False
    assert result.error_kind is ProviderErrorKind.AUTH
    assert "APNS_KEY_FILE" in (result.error_message or "")


@pytest.mark.asyncio
async def test_apns_production_host_when_sandbox_off() -> None:
    seen: dict = {}

    async def fake_post(self, url, **kw):
        seen["url"] = url
        return httpx.Response(
            200, headers={"apns-id": "x"}, request=httpx.Request("POST", url)
        )

    provider = _apns_provider(use_sandbox=False)
    with patch("httpx.AsyncClient.post", fake_post):
        await provider.send(_message())
    assert seen["url"].startswith("https://api.push.apple.com/")


# --------------------------------------------------------------------------- #
# The PUSH_PROVIDER switch (config.py, AI_PROVIDER precedent)
# --------------------------------------------------------------------------- #
class _FakeSettings:
    def __init__(self, **kw):
        self.push_provider = kw.pop("push_provider", "log_only")
        for key, value in kw.items():
            setattr(self, key, value)


def test_factory_defaults_to_log_only_for_every_platform() -> None:
    from oryx.services.activity.providers.push.factory import get_push_provider

    settings = _FakeSettings()  # push_provider unset → "log_only"
    for platform in ("ios", "android", "web"):
        assert get_push_provider(platform, settings).name == "log_only"


def test_factory_real_routes_android_to_fcm_and_ios_to_apns(tmp_path) -> None:
    from oryx.services.activity.providers.push.factory import get_push_provider

    sa_file = tmp_path / "sa.json"
    sa_file.write_text(json.dumps(_fake_service_account()), encoding="utf-8")
    key_file = tmp_path / "key.p8"
    key_file.write_text(_apns_key_pem(), encoding="utf-8")

    settings = _FakeSettings(
        push_provider="real",
        fcm_service_account_file=str(sa_file),
        apns_key_file=str(key_file),
        apns_key_id="K",
        apns_team_id="T",
        apns_topic="com.oryx.app",
        apns_use_sandbox=True,
    )
    assert get_push_provider("android", settings).name == "fcm"
    assert get_push_provider("ios", settings).name == "apns"
    # Browser push is not part of this wave — web stays log-only even on real.
    assert get_push_provider("web", settings).name == "log_only"


def test_factory_real_without_credentials_still_returns_safe_providers() -> None:
    from oryx.services.activity.providers.push.factory import get_push_provider

    settings = _FakeSettings(
        push_provider="real",
        fcm_service_account_file=None,
        apns_key_file=None,
        apns_key_id=None,
        apns_team_id=None,
    )
    # Unconfigured real providers exist and degrade to AUTH results — the
    # switch never crashes dispatch just because credentials are absent.
    assert get_push_provider("android", settings).name == "fcm"
    assert get_push_provider("ios", settings).name == "apns"
