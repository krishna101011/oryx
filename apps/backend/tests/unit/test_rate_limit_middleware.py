"""Tests for the rate limiter's client-address trust boundary."""

from starlette.requests import Request

from oryx.core.middleware import RateLimitMiddleware


def _request(*, client: tuple[str, int] | None, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/v1/auth/signin",
            "raw_path": b"/v1/auth/signin",
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": client,
            "server": ("testserver", 80),
        }
    )


def test_client_key_uses_asgi_peer_not_forwarded_header() -> None:
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(
        client=("198.51.100.24", 12345),
        headers=[(b"x-forwarded-for", b"203.0.113.99")],
    )

    assert middleware._client_key(request) == "198.51.100.24"


def test_client_key_ignores_forwarded_chain_from_request() -> None:
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(
        client=("198.51.100.24", 12345),
        headers=[(b"x-forwarded-for", b"203.0.113.99, 192.0.2.10")],
    )

    assert middleware._client_key(request) == "198.51.100.24"


def test_client_key_falls_back_when_asgi_peer_is_missing() -> None:
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(client=None, headers=[])

    assert middleware._client_key(request) == "unknown"
