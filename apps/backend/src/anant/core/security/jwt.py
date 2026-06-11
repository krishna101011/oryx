"""JWT access tokens.

HS256 in Phase 2. Claims are intentionally minimal:
    sub: account id
    wsp: active workspace id
    sid: session id
    iat, exp, jti

Refresh tokens are opaque (not JWTs) — see passwords.generate_refresh_token.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt

from anant.config import get_settings
from anant.core.errors import AuthRefreshInvalidError, AuthTokenExpiredError

CLOCK_SKEW_SECONDS = 30


@dataclass(frozen=True)
class AccessClaims:
    sub: str  # account_id
    wsp: str  # workspace_id
    sid: str  # session_id
    iat: datetime
    exp: datetime
    jti: str


def issue_access_token(
    account_id: str, workspace_id: str, session_id: str
) -> tuple[str, datetime]:
    """Return (jwt, expires_at)."""
    settings = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": account_id,
        "wsp": workspace_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, exp


def verify_access_token(token: str) -> AccessClaims:
    """Verify signature and expiry. Raise AuthTokenExpiredError on expiry,
    AuthRefreshInvalidError on any other failure (signature, malformed)."""
    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            leeway=CLOCK_SKEW_SECONDS,
        )
    except pyjwt.ExpiredSignatureError as e:
        raise AuthTokenExpiredError() from e
    except pyjwt.InvalidTokenError as e:
        # Don't leak the specific failure reason in the error message.
        raise AuthRefreshInvalidError("Invalid access token") from e

    return AccessClaims(
        sub=payload["sub"],
        wsp=payload["wsp"],
        sid=payload["sid"],
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        jti=payload["jti"],
    )
