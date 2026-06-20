"""OAuth 2.0 client-credentials grant — token endpoint client + in-memory cache.

For oauth2_client_credentials sources, the access token has a TTL and we
re-fetch when it expires. Tokens live in a per-process cache keyed by
(token_url, client_id, scope) so a single sync loop doesn't refetch on
every call.

Why no DB cache:
  - Tokens are derived from credentials we already store; no benefit to
    persisting them.
  - In-memory cache is bounded by process lifetime; restart re-fetches
    on first request (cheap).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

import httpx

from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)


@dataclass(frozen=True)
class _CachedToken:
    access_token: str
    expires_at: float


_CACHE: dict[tuple[str, str, str], _CachedToken] = {}
_CACHE_LOCK = Lock()

# Refresh `n` seconds before actual expiry to avoid race with the vendor.
SAFETY_MARGIN_SECONDS = 30


async def get_client_credentials_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str | None,
) -> str:
    key = (token_url, client_id, scope or "")
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and time.time() + SAFETY_MARGIN_SECONDS < cached.expires_at:
            return cached.access_token

    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope:
        body["scope"] = scope

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                token_url,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"OAuth2 token endpoint unreachable: {e}",
        ) from e

    if resp.status_code in (400, 401, 403):
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message=f"OAuth2 token exchange failed: {resp.status_code}",
        )
    if resp.status_code >= 500:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"OAuth2 token endpoint {resp.status_code}",
        )
    if resp.status_code >= 400:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"OAuth2 token endpoint {resp.status_code}",
        )

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message="OAuth2 response missing access_token",
        )
    expires_in = int(data.get("expires_in", 3599))

    with _CACHE_LOCK:
        _CACHE[key] = _CachedToken(
            access_token=access_token,
            expires_at=time.time() + expires_in,
        )
    return access_token


def _clear_cache_for_tests() -> None:
    """Test-only: wipe the in-memory cache between cases."""
    with _CACHE_LOCK:
        _CACHE.clear()
