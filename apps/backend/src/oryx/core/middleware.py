"""HTTP middleware.

Order matters and is documented in the architecture spec.
The actual application order (outer → inner) is the REVERSE of add order in
main.py — RequestID + Timing get added last so they run first.
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from oryx.config import get_settings

REQUEST_ID_HEADER = "X-Request-Id"
RESPONSE_TIME_HEADER = "X-Response-Time"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limit on /v1/auth/signin, /v1/auth/signup, and
    GET /v1/public/pages/{slug}.

    Counters are in-memory and local to this API process. This is not a
    shared limit across multiple workers or instances; use a shared store or
    edge-level limiter before relying on global limits at scale. Client
    identity comes from the ASGI connection, not raw forwarding headers.
    """

    WINDOW_SECONDS = 600  # 10 minutes

    def __init__(self, app, prefix: str = "/v1") -> None:
        super().__init__(app)
        self.prefix = prefix
        self._signin_hits: dict[str, deque[float]] = {}
        self._signup_hits: dict[str, deque[float]] = {}
        self._public_page_hits: dict[str, deque[float]] = {}
        self._last_bucket_prune = time.monotonic()

    def _client_key(self, request: Request) -> str:
        """Use the ASGI peer address, never a caller-controlled forwarding header.

        If Uvicorn is behind a reverse proxy, its proxy-header handling must be
        restricted to the deployment's exact trusted proxy addresses. Uvicorn
        then supplies the resolved client address through request.client.
        """
        return request.client.host if request.client else "unknown"

    PRUNE_INTERVAL_SECONDS = 60

    def _prune_expired_buckets(self, now: float) -> None:
        """Remove client buckets whose complete sliding window has expired."""
        for hits in (self._signin_hits, self._signup_hits, self._public_page_hits):
            for key, bucket in list(hits.items()):
                while bucket and now - bucket[0] > self.WINDOW_SECONDS:
                    bucket.popleft()
                if not bucket:
                    del hits[key]

    def _check(self, hits: dict[str, deque[float]], key: str, limit: int) -> bool:
        now = time.time()
        monotonic_now = time.monotonic()
        if monotonic_now - self._last_bucket_prune >= self.PRUNE_INTERVAL_SECONDS:
            self._prune_expired_buckets(now)
            self._last_bucket_prune = monotonic_now

        bucket = hits.setdefault(key, deque())
        while bucket and now - bucket[0] > self.WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if request.method == "POST" and path.startswith(self.prefix + "/auth/"):
            settings = get_settings()
            key = self._client_key(request)
            if path.endswith("/signin"):
                if not self._check(
                    self._signin_hits, key, settings.rate_limit_signin_per_10min
                ):
                    return self._rate_limited(request)
            elif path.endswith("/signup"):
                if not self._check(
                    self._signup_hits, key, settings.rate_limit_signup_per_10min
                ):
                    return self._rate_limited(request)
        elif request.method == "GET" and path.startswith(self.prefix + "/public/pages/"):
            settings = get_settings()
            key = self._client_key(request)
            if not self._check(
                self._public_page_hits,
                key,
                settings.rate_limit_public_pages_per_10min,
            ):
                return self._rate_limited(
                    request,
                    code="PUBLIC_PAGE_RATE_LIMITED",
                    message="Too many requests",
                )
        return await call_next(request)

    @staticmethod
    def _rate_limited(
        request: Request,
        *,
        code: str = "AUTH_RATE_LIMITED",
        message: str = "Too many authentication attempts",
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "requestId": request_id,
                }
            },
        )
