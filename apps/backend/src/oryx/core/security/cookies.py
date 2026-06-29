"""Web session cookie — the second half of dual-auth.

Native clients carry the access token in the `Authorization: Bearer` header and
persist it in device secure storage. Web browsers cannot safely hold a token in
JS-readable storage (XSS exfiltration), so on web the same access token rides in
an httpOnly cookie the browser attaches automatically. The auth dependency reads
the header first and falls back to this cookie, so a single validation path
serves both platforms.

`Secure` is omitted in dev so the flag works over plain http://localhost; it is
set everywhere else. `SameSite=Lax` lets top-level navigations send the cookie
while blocking it on cross-site subrequests (CSRF baseline).
"""
from __future__ import annotations

from fastapi import Response

from oryx.config import Settings

SESSION_COOKIE_NAME = "oryx_session"


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "dev",
        path="/",
        max_age=settings.access_token_ttl_minutes * 60,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    # Attributes (path/samesite/secure) must match the set call or the browser
    # treats it as a different cookie and the delete is silently ignored.
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.environment != "dev",
    )
