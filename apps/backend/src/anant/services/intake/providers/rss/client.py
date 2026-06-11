"""HTTP fetch with conditional-request support.

This module is the only place that touches the network. The sync layer
gets back a `FetchResult` and decides what to do with it.

Why httpx and not aiohttp:
- Smaller dependency footprint
- First-class HTTP/2 (matters for some CDNs Substack uses)
- Same client class for sync + async — easier mocking in tests
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import httpx

from anant.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)

DEFAULT_TIMEOUT_SECONDS = 30
MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MiB feed cap; oversized feeds → PERMANENT


class FetchOutcome(str, Enum):
    OK = "ok"
    NOT_MODIFIED = "not_modified"
    REDIRECT_PERMANENT = "redirect_permanent"  # 301 — caller persists new URL (CR-10)


@dataclass(frozen=True)
class FetchResult:
    outcome: FetchOutcome
    body: bytes | None
    etag: str | None
    last_modified: str | None
    content_type: str | None
    final_url: str | None  # set on REDIRECT_PERMANENT


async def fetch_feed(
    url: str,
    *,
    etag: str | None,
    last_modified: str | None,
    user_agent: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> FetchResult:
    """Single feed pull.

    Translates HTTP failures into ProviderError(kind=...) per the typed
    taxonomy. The sync loop never sees a raw httpx exception.
    """
    headers: dict[str, str] = {
        "Accept": "application/atom+xml, application/rss+xml, application/xml;q=0.9, */*;q=0.5",
        "User-Agent": user_agent,
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    try:
        # follow_redirects=False so we control 301 vs 302 semantics ourselves.
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False
        ) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"Timeout fetching {url}: {e}",
            cause_class=type(e).__name__,
        ) from e
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"HTTP error fetching {url}: {e}",
            cause_class=type(e).__name__,
        ) from e

    status = response.status_code

    # CR-10: 301 = persist new URL; 302 = follow once, do not persist
    if status == 301:
        location = response.headers.get("location")
        if not location:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="301 without Location header",
            )
        return FetchResult(
            outcome=FetchOutcome.REDIRECT_PERMANENT,
            body=None,
            etag=None,
            last_modified=None,
            content_type=None,
            final_url=str(httpx.URL(url).join(location)),
        )
    if status == 302 or status == 303 or status == 307 or status == 308:
        location = response.headers.get("location")
        if not location:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="Redirect without Location header",
            )
        # Follow once; reuse this client to keep timeouts honest.
        follow_url = str(httpx.URL(url).join(location))
        return await fetch_feed(
            follow_url,
            etag=etag,
            last_modified=last_modified,
            user_agent=user_agent,
            timeout=timeout,
        )

    if status == 304:
        return FetchResult(
            outcome=FetchOutcome.NOT_MODIFIED,
            body=None,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            content_type=None,
            final_url=None,
        )

    if status == 401 or status == 403:
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message=f"Auth failure ({status})",
        )
    if status == 429:
        retry_after = _parse_retry_after(response.headers.get("retry-after"))
        raise ProviderError(
            kind=ProviderErrorKind.RATE_LIMITED,
            message="Rate limited",
            retry_after_seconds=retry_after,
        )
    if 400 <= status < 500:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Client error {status}",
        )
    if status >= 500:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"Server error {status}",
        )

    body = response.content
    if len(body) > MAX_BODY_BYTES:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Feed body exceeds {MAX_BODY_BYTES} bytes",
        )

    return FetchResult(
        outcome=FetchOutcome.OK,
        body=body,
        etag=response.headers.get("etag"),
        last_modified=response.headers.get("last-modified"),
        content_type=response.headers.get("content-type"),
        final_url=str(response.url),
    )


def _parse_retry_after(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        # HTTP-date form is also valid; we don't parse it in Batch 2.
        return None
