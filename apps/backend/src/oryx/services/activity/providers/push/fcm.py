"""FCMProvider — real Android push via the FCM HTTP v1 API (Phase 6 Wave C).

Complete implementation against the real wire protocol, proven with a faked
httpx layer (tests/unit/test_push_providers.py) — the same standard Phase 5
Wave D set for the social channels. No live Firebase account is needed to
prove correctness.

PRODUCTION CREDENTIALS (documented requirement, not defaulted):
  A Firebase service-account key file — Firebase console → Project settings →
  Service accounts → "Generate new private key". Point
  FCM_SERVICE_ACCOUNT_FILE (config.py) at the downloaded JSON; project id,
  client email, and the RSA signing key are all read from it. Without it every
  send returns ok=False / error_kind=AUTH — it never raises.

Wire shape (two requests per cold send):
  1. OAuth2 JWT-bearer grant: a RS256-signed JWT (iss=client_email,
     scope=firebase.messaging, aud=token_uri) exchanged at token_uri for a
     ~1h access token. Cached per client_email until 60s before expiry.
  2. POST https://fcm.googleapis.com/v1/projects/{project}/messages:send with
     {"message": {"token", "notification", "data"}}. FCM requires data values
     to be strings, so they are stringified here.
"""
from __future__ import annotations

import time as _time
from typing import Any

import httpx
import jwt

from oryx.core.logging import get_logger

from .base import ProviderErrorKind, ProviderResult, PushMessage

logger = get_logger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
_TOKEN_TTL_SECONDS = 3600
_TOKEN_LEEWAY_SECONDS = 60

# access-token cache: client_email -> (token, absolute expiry epoch seconds).
# Module-level so the per-send provider instances the factory hands out still
# share one token per service account.
_token_cache: dict[str, tuple[str, float]] = {}


def _status_to_error_kind(status: int) -> ProviderErrorKind:
    if status in (401, 403):
        return ProviderErrorKind.AUTH
    if status == 429:
        return ProviderErrorKind.RATE_LIMITED
    if status in (400, 404):
        # INVALID_ARGUMENT / UNREGISTERED — the token is bad or gone; retrying
        # the same token can never succeed.
        return ProviderErrorKind.PERMANENT
    if status >= 500:
        return ProviderErrorKind.TRANSIENT
    return ProviderErrorKind.UNKNOWN


class FCMProvider:
    """PushProvider implementation for Android device tokens."""

    name = "fcm"

    def __init__(
        self, service_account: dict[str, Any] | None, *, timeout: float = 10.0
    ) -> None:
        # The parsed service-account JSON (project_id / client_email /
        # private_key / token_uri). None means "not configured": send()
        # degrades to an AUTH failure result instead of raising.
        self._sa = service_account
        self._timeout = timeout

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        assert self._sa is not None  # guarded by send()
        email = str(self._sa["client_email"])
        cached = _token_cache.get(email)
        now = _time.time()
        if cached and cached[1] - _TOKEN_LEEWAY_SECONDS > now:
            return cached[0]

        token_uri = str(self._sa.get("token_uri") or _DEFAULT_TOKEN_URI)
        assertion = jwt.encode(
            {
                "iss": email,
                "scope": _SCOPE,
                "aud": token_uri,
                "iat": int(now),
                "exp": int(now) + _TOKEN_TTL_SECONDS,
            },
            self._sa["private_key"],
            algorithm="RS256",
        )
        resp = await client.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        access_token = str(payload["access_token"])
        expires_in = float(payload.get("expires_in", _TOKEN_TTL_SECONDS))
        _token_cache[email] = (access_token, now + expires_in)
        return access_token

    async def send(self, message: PushMessage) -> ProviderResult:
        if not self._sa or not self._sa.get("client_email") or not self._sa.get(
            "private_key"
        ):
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message=(
                    "FCM service account not configured "
                    "(set FCM_SERVICE_ACCOUNT_FILE)"
                ),
            )

        notification: dict[str, str] = {"title": message.title}
        if message.body:
            notification["body"] = message.body
        body = {
            "message": {
                "token": message.token,
                "notification": notification,
                # FCM v1 rejects non-string data values.
                "data": {k: str(v) for k, v in message.data.items()},
            }
        }
        url = (
            "https://fcm.googleapis.com/v1/projects/"
            f"{self._sa.get('project_id', '')}/messages:send"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                access_token = await self._access_token(client)
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=body,
                )
        except httpx.HTTPStatusError as exc:
            # The OAuth token exchange failed (raise_for_status in
            # _access_token) — classify by ITS status, e.g. 401 → AUTH.
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=_status_to_error_kind(exc.response.status_code),
                error_message=f"fcm token exchange {exc.response.status_code}",
            )
        except httpx.HTTPError as exc:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.TRANSIENT,
                error_message=f"fcm unreachable: {exc}",
            )

        if resp.status_code == 200:
            message_id = resp.json().get("name")
            logger.info("push.send.fcm", extra={"message_id": message_id})
            return ProviderResult(ok=True, provider=self.name, message_id=message_id)

        return ProviderResult(
            ok=False,
            provider=self.name,
            error_kind=_status_to_error_kind(resp.status_code),
            error_message=f"fcm {resp.status_code}: {resp.text[:200]}",
        )
