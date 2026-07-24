"""Webhook channel adapter (§10.2 / §13.4).

POSTs a JSON payload to config.url, signed with HMAC-SHA256 over
"{timestamp}.{body}" using credentials.secret. Headers:
    X-Oryx-Signature: sha256=<hex>
    X-Oryx-Timestamp: <unix-seconds>

The X-Oryx-* names match the post-rename convention ORYX's own inbound webhook
receiver uses (Phase 3 §6.2), so an ORYX-style receiver can verify with the same
scheme. Retries up to 3 times internally on transient failures with a short
backoff, then raises TransientChannelError up to the engine (which applies the
outer 5-attempt outbox policy).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from oryx.core.security.ssrf import UnsafeUrlError
from oryx.core.security.ssrf import assert_url_safe as _assert_url_safe
from oryx.services.publishing.channels.base import (
    PermanentChannelError,
    PublishResult,
    TransientChannelError,
)
from oryx.services.publishing.channels.formatting import single_segment
from oryx.services.publishing.citations import CitationSummary

_INTERNAL_ATTEMPTS = 3


def sign_payload(*, secret: str, timestamp: int, body: bytes) -> str:
    """Return the X-Oryx-Signature value: 'sha256=' + hex(HMAC-SHA256)."""
    payload = f"{timestamp}.".encode("ascii") + body
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class WebhookChannel:
    channel_type = "webhook"

    def __init__(self, timeout: float = 15.0, backoff_base: float = 0.5) -> None:
        self._timeout = timeout
        self._backoff_base = backoff_base

    async def validate_credentials(self, credentials: dict[str, Any]) -> bool:
        return bool(credentials.get("secret"))

    async def health_check(self, credentials: dict[str, Any]) -> bool:
        # No standard liveness endpoint for arbitrary webhooks; a configured
        # secret is the strongest signal we have without sending a real payload.
        return bool(credentials.get("secret"))

    def format_content(self, content: str, max_length: int | None) -> list[str]:
        return single_segment(content, max_length)

    async def publish(
        self,
        content: str,
        draft_title: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
        citations: list[CitationSummary] | None = None,
    ) -> PublishResult:
        url = config.get("url")
        secret = credentials.get("secret")
        if not url:
            raise PermanentChannelError(f"{self.channel_type}: config.url is required")
        if not isinstance(url, str):
            raise PermanentChannelError(f"{self.channel_type}: config.url must be a string")
        if not secret:
            raise PermanentChannelError(
                f"{self.channel_type}: credentials.secret is required"
            )
        # config.url has no pydantic schema behind it (unlike RSS's HttpUrl
        # feed_url) — this guard is the only place scheme + SSRF are checked.
        try:
            _assert_url_safe(url)
        except UnsafeUrlError as e:
            raise PermanentChannelError(f"{self.channel_type}: {e}") from e

        payload: dict[str, Any] = {
            "title": draft_title,
            "content": content,
            "published_at": int(time.time()),
        }
        # Citations ride as a distinct structured field, NEVER mixed into content
        # (the webhook feeds other systems, not human readers). Default None keeps
        # any pre-patch call site backward-compatible; an explicit [] is sent as
        # an empty array for a zero-citation draft.
        if citations is not None:
            payload["citations"] = [
                {
                    "headline": c.headline,
                    "confidenceTier": c.confidence_tier,
                    "epistemicType": c.epistemic_type,
                }
                for c in citations
            ]
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        timestamp = int(time.time())
        headers = {
            "content-type": "application/json",
            "X-Oryx-Signature": sign_payload(
                secret=secret, timestamp=timestamp, body=body
            ),
            "X-Oryx-Timestamp": str(timestamp),
        }

        last_error: str | None = None
        for attempt in range(_INTERNAL_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, headers=headers, content=body)
            except httpx.HTTPError as exc:
                last_error = f"unreachable: {exc}"
            else:
                code = resp.status_code
                if code < 400:
                    ext_id = None
                    try:
                        ext_id = (resp.json() or {}).get("id")
                    except (ValueError, TypeError):
                        ext_id = None
                    return PublishResult(
                        external_id=ext_id, external_url=url, status="delivered"
                    )
                if code in (401, 403):
                    raise PermanentChannelError(
                        f"{self.channel_type}: auth rejected ({code})"
                    )
                if code != 429 and code < 500:
                    raise PermanentChannelError(
                        f"{self.channel_type}: rejected ({code})"
                    )
                last_error = f"retryable {code}"
            # transient — back off and retry (skip sleep after the last attempt)
            if attempt < _INTERNAL_ATTEMPTS - 1:
                await asyncio.sleep(self._backoff_base * (2 ** attempt))

        raise TransientChannelError(
            f"{self.channel_type}: failed after {_INTERNAL_ATTEMPTS} attempts: {last_error}"
        )
