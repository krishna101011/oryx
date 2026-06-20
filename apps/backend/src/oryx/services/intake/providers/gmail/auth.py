"""Gmail OAuth 2.0 — start, callback exchange, refresh, revoke.

Design:
  - We use the web-server flow with `offline` access type to get a refresh token.
  - State is a signed short-lived JWT carrying the return context. No
    server-side state table.
  - Refresh failure → ProviderError(kind=AUTH). The intake service then sets
    the source to `auth_required` per the retry classifier.
  - Revoke calls Google's revoke endpoint best-effort; even if it fails we
    delete the local credentials.

What we deliberately do NOT do:
  - Request any scope other than gmail.readonly (asserted by REQUESTED_SCOPES).
  - Persist anything until the code exchange has succeeded.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt as pyjwt

from oryx.config import get_settings
from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)
from oryx.services.intake.providers.gmail.config_schema import (
    GMAIL_OAUTH_AUTH_URL,
    GMAIL_OAUTH_TOKEN_URL,
    REQUESTED_SCOPES,
)

STATE_TTL_SECONDS = 600  # 10 min — well under the user's attention span


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str | None
    expires_in_seconds: int
    scope: str
    token_type: str


@dataclass(frozen=True)
class StateClaims:
    workspace_id: uuid.UUID
    account_id: uuid.UUID
    intake_source_id: uuid.UUID
    csrf: str


# ---------------------------------------------------------------------------
# State (CSRF + return context)
# ---------------------------------------------------------------------------

def _state_secret() -> str:
    # Re-uses the JWT secret. State JWTs are short-lived (10 min) so this is
    # an acceptable cohabitation; we never sign access tokens here.
    return get_settings().jwt_secret


def encode_state(
    *, workspace_id: uuid.UUID, account_id: uuid.UUID, intake_source_id: uuid.UUID
) -> str:
    payload = {
        "wsp": str(workspace_id),
        "acc": str(account_id),
        "src": str(intake_source_id),
        "csrf": uuid.uuid4().hex,
        "iat": int(time.time()),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    return pyjwt.encode(payload, _state_secret(), algorithm="HS256")


def decode_state(state: str) -> StateClaims:
    try:
        payload = pyjwt.decode(state, _state_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError as e:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT, message="OAuth state expired"
        ) from e
    except pyjwt.InvalidTokenError as e:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT, message="OAuth state invalid"
        ) from e
    return StateClaims(
        workspace_id=uuid.UUID(payload["wsp"]),
        account_id=uuid.UUID(payload["acc"]),
        intake_source_id=uuid.UUID(payload["src"]),
        csrf=payload["csrf"],
    )


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------

def build_auth_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Build the consent URL we send the user to."""
    # Assertion: scopes list MUST be exactly the readonly scope.
    if REQUESTED_SCOPES != ("https://www.googleapis.com/auth/gmail.readonly",):
        raise RuntimeError("Gmail scope set has been tampered with — ADR-023 violation")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(REQUESTED_SCOPES),
        "access_type": "offline",   # required for refresh token
        "prompt": "consent",        # force refresh-token issuance every connect
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GMAIL_OAUTH_AUTH_URL}?{urlencode(params)}"


# ---------------------------------------------------------------------------
# Code exchange + refresh
# ---------------------------------------------------------------------------

async def exchange_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> TokenBundle:
    body = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    return await _post_token(body)


async def refresh_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> TokenBundle:
    body = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    return await _post_token(body)


async def revoke_token(refresh_or_access_token: str) -> bool:
    """Best-effort revoke. Returns True on success; logs nothing on failure."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": refresh_or_access_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return resp.status_code in (200, 400)  # 400 = already revoked
    except httpx.HTTPError:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _post_token(body: dict[str, str]) -> TokenBundle:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GMAIL_OAUTH_TOKEN_URL,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"OAuth token endpoint unreachable: {e}",
        ) from e

    if resp.status_code in (400, 401):
        # Google returns 400 on invalid_grant; treat as AUTH so the source
        # is marked auth_required and the user must reconnect.
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message=f"OAuth token exchange failed: {resp.text[:200]}",
        )
    if resp.status_code >= 500:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"OAuth token endpoint {resp.status_code}",
        )
    if resp.status_code >= 400:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"OAuth token endpoint {resp.status_code}: {resp.text[:200]}",
        )

    data: dict[str, Any] = resp.json()
    granted_scope = data.get("scope", "")
    # Defense in depth: if Google ever returns a broader scope, refuse.
    requested_set = set(REQUESTED_SCOPES)
    granted_set = set(granted_scope.split())
    if not requested_set.issubset(granted_set):
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message="Granted scope does not include gmail.readonly",
        )

    return TokenBundle(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in_seconds=int(data.get("expires_in", 3599)),
        scope=granted_scope,
        token_type=data.get("token_type", "Bearer"),
    )
