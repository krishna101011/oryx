"""APNsProvider — real iOS push via Apple's APNs HTTP/2 API (Phase 6 Wave C).

Complete implementation against the real wire protocol, proven with a faked
httpx layer (tests/unit/test_push_providers.py) — same standard as Phase 5
Wave D's social channels. No Apple developer account is needed to prove
correctness.

PRODUCTION CREDENTIALS (documented requirement, not defaulted):
  A token-auth APNs key — developer.apple.com → Certificates, Identifiers &
  Profiles → Keys → new key with "Apple Push Notifications service" enabled.
  Configure (config.py): APNS_KEY_FILE (the downloaded .p8), APNS_KEY_ID (the
  10-char key id), APNS_TEAM_ID (the developer team id). APNS_TOPIC must be
  the app bundle id (defaults to com.oryx.app) and APNS_USE_SANDBOX selects
  the sandbox vs production APNs host (sandbox matches development builds).
  Without these every send returns ok=False / error_kind=AUTH — never raises.

Wire shape: POST https://{host}/3/device/{token} over HTTP/2 (Apple requires
HTTP/2 — hence the `h2` dependency), authenticated with an ES256 provider
JWT (iss=team id, kid header=key id; Apple accepts a token for 20-60 min, so
it is cached ~40 min per key id).
"""
from __future__ import annotations

import time as _time

import httpx
import jwt

from oryx.core.logging import get_logger

from .base import ProviderErrorKind, ProviderResult, PushMessage

logger = get_logger(__name__)

_PROD_HOST = "https://api.push.apple.com"
_SANDBOX_HOST = "https://api.sandbox.push.apple.com"
# Apple accepts provider tokens between 20 and 60 minutes old; re-mint at 40.
_TOKEN_TTL_SECONDS = 40 * 60

# provider-token cache: key_id -> (jwt, minted-at epoch seconds). Module-level
# so per-send instances share one token per key.
_token_cache: dict[str, tuple[str, float]] = {}


def _status_to_error_kind(status: int) -> ProviderErrorKind:
    if status in (401, 403):
        return ProviderErrorKind.AUTH
    if status == 429:
        return ProviderErrorKind.RATE_LIMITED
    if status in (400, 404, 410):
        # BadDeviceToken / bad path / Unregistered — retrying the same token
        # can never succeed.
        return ProviderErrorKind.PERMANENT
    if status >= 500:
        return ProviderErrorKind.TRANSIENT
    return ProviderErrorKind.UNKNOWN


class APNsProvider:
    """PushProvider implementation for iOS device tokens."""

    name = "apns"

    def __init__(
        self,
        *,
        key_pem: str | None,
        key_id: str | None,
        team_id: str | None,
        topic: str = "com.oryx.app",
        use_sandbox: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self._key_pem = key_pem
        self._key_id = key_id
        self._team_id = team_id
        self._topic = topic
        self._host = _SANDBOX_HOST if use_sandbox else _PROD_HOST
        self._timeout = timeout

    def _provider_token(self) -> str:
        assert self._key_pem and self._key_id and self._team_id  # guarded by send()
        cached = _token_cache.get(self._key_id)
        now = _time.time()
        if cached and now - cached[1] < _TOKEN_TTL_SECONDS:
            return cached[0]
        token = jwt.encode(
            {"iss": self._team_id, "iat": int(now)},
            self._key_pem,
            algorithm="ES256",
            headers={"kid": self._key_id},
        )
        _token_cache[self._key_id] = (token, now)
        return token

    async def send(self, message: PushMessage) -> ProviderResult:
        if not (self._key_pem and self._key_id and self._team_id):
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message=(
                    "APNs key not configured "
                    "(set APNS_KEY_FILE / APNS_KEY_ID / APNS_TEAM_ID)"
                ),
            )

        alert: dict[str, str] = {"title": message.title}
        if message.body:
            alert["body"] = message.body
        # Custom data rides top-level beside `aps`, per Apple's payload rules.
        body = {"aps": {"alert": alert}, **message.data}
        try:
            provider_token = self._provider_token()
        except Exception as exc:  # malformed key material must not crash dispatch
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.AUTH,
                error_message=f"apns token mint failed: {exc}",
            )

        try:
            async with httpx.AsyncClient(http2=True, timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._host}/3/device/{message.token}",
                    headers={
                        "authorization": f"bearer {provider_token}",
                        "apns-topic": self._topic,
                        "apns-push-type": "alert",
                        "apns-priority": "10",
                    },
                    json=body,
                )
        except httpx.HTTPError as exc:
            return ProviderResult(
                ok=False,
                provider=self.name,
                error_kind=ProviderErrorKind.TRANSIENT,
                error_message=f"apns unreachable: {exc}",
            )

        if resp.status_code == 200:
            message_id = resp.headers.get("apns-id")
            logger.info("push.send.apns", extra={"message_id": message_id})
            return ProviderResult(ok=True, provider=self.name, message_id=message_id)

        reason = ""
        try:
            reason = str(resp.json().get("reason", ""))
        except ValueError:
            pass
        return ProviderResult(
            ok=False,
            provider=self.name,
            error_kind=_status_to_error_kind(resp.status_code),
            error_message=f"apns {resp.status_code}: {reason or resp.text[:200]}",
        )
