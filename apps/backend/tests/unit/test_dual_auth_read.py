"""Dual-auth token extraction: Authorization header first, session cookie fallback.

These exercise the pure read logic (no DB, no JWT verify) that lets one auth
dependency serve native (bearer header) and web (httpOnly cookie) simultaneously.
"""
from __future__ import annotations

from starlette.requests import Request

from oryx.core.dependencies import _read_token
from oryx.core.security.cookies import SESSION_COOKIE_NAME


def _request(headers: dict[str, str]) -> Request:
    raw = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
    ]
    return Request({"type": "http", "headers": raw})


def test_reads_bearer_header() -> None:
    req = _request({"authorization": "Bearer native-token"})
    assert _read_token(req) == "native-token"


def test_falls_back_to_session_cookie() -> None:
    req = _request({"cookie": f"{SESSION_COOKIE_NAME}=web-token"})
    assert _read_token(req) == "web-token"


def test_header_wins_over_cookie() -> None:
    req = _request(
        {
            "authorization": "Bearer native-token",
            "cookie": f"{SESSION_COOKIE_NAME}=web-token",
        }
    )
    assert _read_token(req) == "native-token"


def test_no_token_anywhere() -> None:
    assert _read_token(_request({})) is None


def test_blank_cookie_is_ignored() -> None:
    req = _request({"cookie": f"{SESSION_COOKIE_NAME}="})
    assert _read_token(req) is None
