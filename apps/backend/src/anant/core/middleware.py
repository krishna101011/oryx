"""HTTP middleware.

Order matters and is documented in the architecture spec.
The actual application order (outer → inner) is the REVERSE of add order in
main.py — RequestID + Timing get added last so they run first.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from anant.config import get_settings

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
    """Sliding-window rate limit on /v1/auth/signin and /v1/auth/signup.

    Phase 2: in-memory per-process. Acceptable for a single-instance dev/prod.
    Replace with Redis-backed when we scale horizontally.
    """

    WINDOW_SECONDS = 600  # 10 minutes

    def __init__(self, app, prefix: str = "/v1") -> None:
        super().__init__(app)
        self.prefix = prefix
        self._signin_hits: dict[str, deque[float]] = defaultdict(deque)
        self._signup_hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check(self, hits: dict[str, deque[float]], key: str, limit: int) -> bool:
        now = time.time()
        bucket = hits[key]
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
        return await call_next(request)

    @staticmethod
    def _rate_limited(request: Request) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "AUTH_RATE_LIMITED",
                    "message": "Too many authentication attempts",
                    "requestId": request_id,
                }
            },
        )
