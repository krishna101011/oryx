"""Pydantic contract round-trips.

If the mobile app sends a wire shape, the backend must parse it. If the
backend emits one, mobile must accept it (via the TS interface mirror).
These tests pin the canonical contracts.
"""
from __future__ import annotations

from datetime import UTC, datetime

from oryx.shared.types import (
    ApiError,
    ApiErrorBody,
    ApiResponse,
    HealthStatus,
    MeResponse,
    OnboardingStepRequest,
    SigninRequest,
    SignupRequest,
    TokenPair,
)


def test_api_response_envelope_with_data() -> None:
    payload = ApiResponse[HealthStatus](
        data=HealthStatus(
            status="ok", service="oryx-backend", environment="dev",
            serverTime=datetime.now(UTC),
        ),
    )
    j = payload.model_dump(by_alias=True)
    assert j["data"]["status"] == "ok"
    assert j["data"]["serverTime"] is not None


def test_api_error_envelope_serializes_with_aliases() -> None:
    body = ApiErrorBody(code="AUTH_REQUIRED", message="x", requestId="r-1")
    env = ApiError(error=body)
    j = env.model_dump(by_alias=True)
    assert j["error"]["code"] == "AUTH_REQUIRED"
    assert j["error"]["requestId"] == "r-1"


def test_signup_request_parses_camel_case() -> None:
    body = SignupRequest.model_validate({
        "email": "a@b.com",
        "password": "StrongPass123",
        "displayName": "A",
        "deviceId": "d-1",
        "deviceLabel": "iPhone",
        "devicePlatform": "ios",
    })
    assert body.display_name == "A"
    assert body.device_platform == "ios"


def test_signin_request_round_trips() -> None:
    src = {
        "email": "x@y.com", "password": "p",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "android",
    }
    parsed = SigninRequest.model_validate(src)
    re = parsed.model_dump(by_alias=True)
    assert re["devicePlatform"] == "android"


def test_token_pair_emits_camel_case() -> None:
    now = datetime.now(UTC)
    t = TokenPair(
        accessToken="a", refreshToken="r",
        accessTokenExpiresAt=now, refreshTokenExpiresAt=now,
        sessionId="s", accountId="acc",
    )
    j = t.model_dump(by_alias=True)
    assert {"accessToken", "refreshToken", "accessTokenExpiresAt",
            "refreshTokenExpiresAt", "sessionId", "accountId"} <= set(j.keys())


def test_me_response_full_envelope() -> None:
    now = datetime.now(UTC)
    me = MeResponse.model_validate({
        "account": {
            "id": "a", "email": "x@y.com", "status": "active",
            "emailVerified": False, "createdAt": now,
        },
        "profile": {
            "accountId": "a", "displayName": "A", "timezone": "UTC",
            "locale": "en-US", "createdAt": now, "updatedAt": now,
            "avatarUrl": None, "headline": None,
        },
        "workspace": {"id": "w", "name": "W", "kind": "personal", "role": "owner"},
        "preferences": {
            "accountId": "a", "focus": "both", "contentStyle": "balanced",
            "verificationStrictness": "balanced", "notificationFrequency": "daily",
            "customTopics": [], "createdAt": now, "updatedAt": now,
        },
        "activity": {"unreadCount": 0},
        "flags": {"ff_settings": True, "ff_dashboard": True},
        "onboarding": {"state": "complete", "nextStep": None},
        "verification": {"pendingReviewCount": 3, "openConflictCount": 1, "verifiedCount": 5},
        "research": {"activeWorkspaceCount": 2, "readyPacketCount": 0},
        "content": {
            "draftCount": 4, "pendingReviewCount": 1,
            "scheduledCount": 0, "publishedThisWeek": 2,
        },
        "serverTime": now,
        "build": {"version": "0.1.0", "commit": "dev"},
    })
    j = me.model_dump(by_alias=True)
    assert j["workspace"]["role"] == "owner"
    assert j["onboarding"]["state"] == "complete"
    assert j["activity"]["unreadCount"] == 0
    assert j["verification"]["pendingReviewCount"] == 3
    assert j["verification"]["verifiedCount"] == 5
    assert j["research"]["readyPacketCount"] == 0
    assert j["content"]["draftCount"] == 4
    assert j["content"]["publishedThisWeek"] == 2


def test_onboarding_step_request_accepts_partial_payload() -> None:
    # Only fields relevant to step 2 are sent.
    body = OnboardingStepRequest.model_validate({
        "step": "focus_sources",
        "focus": "crypto",
        "enabledSourceKeys": ["coindesk", "the_block"],
    })
    assert body.focus == "crypto"
    assert body.enabled_source_keys == ["coindesk", "the_block"]
    assert body.notification_frequency is None  # not sent
