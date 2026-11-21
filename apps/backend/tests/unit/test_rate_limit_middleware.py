"""Tests for the rate limiter's client-address trust boundary."""

from collections import deque

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


def test_prune_expired_buckets_removes_stale_entries_from_every_route_bucket() -> None:
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    now = 10_000.0
    expired_at = now - middleware.WINDOW_SECONDS - 1

    middleware._signin_hits["old-signin"] = deque([expired_at])
    middleware._signup_hits["old-signup"] = deque([expired_at])
    middleware._public_page_hits["old-public"] = deque([expired_at])
    middleware._signin_hits["active-signin"] = deque([now - 10])

    middleware._prune_expired_buckets(now)

    assert "old-signin" not in middleware._signin_hits
    assert "old-signup" not in middleware._signup_hits
    assert "old-public" not in middleware._public_page_hits
    assert list(middleware._signin_hits["active-signin"]) == [now - 10]


def test_check_triggers_periodic_pruning_across_route_bucket_maps(monkeypatch) -> None:
    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    expired_at = 100.0
    middleware._signin_hits["stale-signin"] = deque([expired_at])
    middleware._signup_hits["stale-signup"] = deque([expired_at])
    middleware._public_page_hits["stale-public"] = deque([expired_at])
    middleware._last_bucket_prune = 0.0
    monkeypatch.setattr("oryx.core.middleware.time.time", lambda: 1_000.0)
    monkeypatch.setattr("oryx.core.middleware.time.monotonic", lambda: 61.0)

    assert middleware._check(middleware._signin_hits, "current-client", 5) is True

    assert "stale-signin" not in middleware._signin_hits
    assert "stale-signup" not in middleware._signup_hits
    assert "stale-public" not in middleware._public_page_hits
    assert list(middleware._signin_hits["current-client"]) == [1_000.0]
