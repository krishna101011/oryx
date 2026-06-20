"""JWT signing and verification."""
from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import jwt as pyjwt
import pytest

from oryx.config import get_settings
from oryx.core.errors import AuthRefreshInvalidError, AuthTokenExpiredError
from oryx.core.security.jwt import issue_access_token, verify_access_token


def _ids() -> tuple[str, str, str]:
    return str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())


def test_issue_and_verify_round_trips() -> None:
    a, w, s = _ids()
    token, exp = issue_access_token(a, w, s)
    claims = verify_access_token(token)
    assert claims.sub == a
    assert claims.wsp == w
    assert claims.sid == s
    assert claims.exp.tzinfo is not None
    assert claims.exp > datetime.now(UTC)
    # JWT exp claim is integer-seconds; compare at that resolution.
    assert int(exp.timestamp()) == int(claims.exp.timestamp())


def test_claim_shape_is_minimal() -> None:
    a, w, s = _ids()
    token, _ = issue_access_token(a, w, s)
    settings = get_settings()
    payload = pyjwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert set(payload.keys()) == {"sub", "wsp", "sid", "iat", "exp", "jti"}


def test_jti_is_unique_per_issue() -> None:
    a, w, s = _ids()
    token1, _ = issue_access_token(a, w, s)
    token2, _ = issue_access_token(a, w, s)
    c1 = verify_access_token(token1)
    c2 = verify_access_token(token2)
    assert c1.jti != c2.jti


def test_expired_token_raises_token_expired_error() -> None:
    settings = get_settings()
    a, w, s = _ids()
    expired = {
        "sub": a, "wsp": w, "sid": s,
        "iat": int(time.time()) - 3600,
        "exp": int(time.time()) - 1800,
        "jti": str(uuid.uuid4()),
    }
    token = pyjwt.encode(expired, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(AuthTokenExpiredError):
        verify_access_token(token)


def test_invalid_signature_raises_refresh_invalid_error() -> None:
    a, w, s = _ids()
    bogus = pyjwt.encode(
        {
            "sub": a, "wsp": w, "sid": s,
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
            "jti": "x",
        },
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(AuthRefreshInvalidError):
        verify_access_token(bogus)


def test_malformed_token_raises_refresh_invalid_error() -> None:
    with pytest.raises(AuthRefreshInvalidError):
        verify_access_token("not.a.jwt")


def test_clock_skew_tolerance_accepts_recently_expired_token() -> None:
    settings = get_settings()
    a, w, s = _ids()
    # 10s past expiry — within the 30s leeway.
    almost = {
        "sub": a, "wsp": w, "sid": s,
        "iat": int(time.time()) - 100,
        "exp": int(time.time()) - 10,
        "jti": str(uuid.uuid4()),
    }
    token = pyjwt.encode(almost, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    # Should NOT raise.
    verify_access_token(token)
