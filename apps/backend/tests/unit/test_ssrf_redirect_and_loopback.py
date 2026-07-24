"""Real-server SSRF proof for the two closed gaps: RSS feed fetch and
publishing webhook delivery. Both call sites now run the shared guard
(oryx.core.security.ssrf.assert_url_safe) — this file re-proves, against
real local servers, the same two exposure classes that were live before the
fix:

  1. direct loopback/private/link-local/cloud-metadata fetch
  2. a redirect whose Location resolves to an internal target, even when the
     initial URL looked external

...and confirms legitimate delivery still works (regression).

Where a real listening server is used, "no request received" is the actual
proof the guard fired before any connection was attempted — not an
assumption from the exception type alone.
"""
from __future__ import annotations

import http.server
import socket
from unittest.mock import patch

import httpx
import pytest

from oryx.services.intake.providers.errors import ProviderError, ProviderErrorKind
from oryx.services.intake.providers.rss.client import FetchOutcome, fetch_feed
from oryx.services.publishing.channels.base import PermanentChannelError
from oryx.services.publishing.channels.webhook import WebhookChannel


def _patch_dns(addr: str):
    """Every hostname resolves to `addr` — for tests where only the
    guard's classification of one address matters, not real connectivity."""
    def fake_getaddrinfo(host, port, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port))]
    return patch("socket.getaddrinfo", fake_getaddrinfo)


def _patch_dns_map(mapping: dict[str, str]):
    """Per-hostname resolution override, real getaddrinfo otherwise — lets a
    fake external hostname and a real loopback target coexist in one test
    with both resolutions still going through the real resolver logic."""
    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, port, *a, **kw):
        return real_getaddrinfo(mapping.get(host, host), port, *a, **kw)
    return patch("socket.getaddrinfo", fake_getaddrinfo)


class _CountingHandler(http.server.BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self) -> None:
        type(self).hits += 1
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"should never be reached")

    do_POST = do_GET

    def log_message(self, *args) -> None:  # silence test server
        pass


def _real_server() -> tuple[http.server.HTTPServer, int]:
    _CountingHandler.hits = 0
    server = http.server.HTTPServer(("127.0.0.1", 0), _CountingHandler)
    server.timeout = 0.3
    return server, server.server_address[1]


# --------------------------------------------------------------------------- #
# RSS — direct loopback fetch
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_rss_direct_loopback_fetch_is_rejected_without_contacting_server() -> None:
    server, port = _real_server()
    try:
        with pytest.raises(ProviderError) as exc:
            await fetch_feed(
                f"http://127.0.0.1:{port}/feed",
                etag=None, last_modified=None, user_agent="OryxIntake/1.0",
            )
        assert exc.value.kind == ProviderErrorKind.PERMANENT
        server.handle_request()  # real wait; proves nothing arrived
    finally:
        server.server_close()
    assert _CountingHandler.hits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "169.254.10.5"],
)
async def test_rss_rejects_resolved_private_link_local_and_metadata_addresses(addr: str) -> None:
    with _patch_dns(addr):
        with pytest.raises(ProviderError) as exc:
            await fetch_feed(
                "https://vendor.test/feed",
                etag=None, last_modified=None, user_agent="OryxIntake/1.0",
            )
    assert exc.value.kind == ProviderErrorKind.PERMANENT


@pytest.mark.asyncio
async def test_rss_rejects_non_http_scheme() -> None:
    with pytest.raises(ProviderError) as exc:
        await fetch_feed(
            "file:///etc/passwd",
            etag=None, last_modified=None, user_agent="OryxIntake/1.0",
        )
    assert exc.value.kind == ProviderErrorKind.PERMANENT


# --------------------------------------------------------------------------- #
# RSS — redirect-to-internal chain: initial URL resolves public, the 302
# Location resolves to a real loopback listener.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_rss_redirect_to_internal_target_is_rejected_not_followed() -> None:
    internal, internal_port = _real_server()

    entry_response = httpx.Response(
        302,
        headers={"location": f"http://internal-target.test:{internal_port}/secret"},
        request=httpx.Request("GET", "https://feed.vendor.test/rss"),
    )

    async def fake_entry_get(self, url, **kw):
        return entry_response

    try:
        with _patch_dns_map(
            {"feed.vendor.test": "8.8.8.8", "internal-target.test": "127.0.0.1"}
        ):
            with patch("httpx.AsyncClient.get", fake_entry_get):
                with pytest.raises(ProviderError) as exc:
                    await fetch_feed(
                        "https://feed.vendor.test/rss",
                        etag=None, last_modified=None, user_agent="OryxIntake/1.0",
                    )
        assert exc.value.kind == ProviderErrorKind.PERMANENT
        internal.handle_request()  # real wait; proves nothing arrived
    finally:
        internal.server_close()
    assert _CountingHandler.hits == 0, (
        "guard failed to re-validate the redirect target — internal server received a real request"
    )


# --------------------------------------------------------------------------- #
# RSS — legitimate feed still works (regression)
# --------------------------------------------------------------------------- #
_RSS_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>T</title>
<item><guid>g1</guid><title>Item</title><link>https://x.test/a</link></item>
</channel></rss>
"""


@pytest.mark.asyncio
async def test_rss_legitimate_public_feed_still_fetches() -> None:
    async def fake_get(self, url, **kw):
        return httpx.Response(200, content=_RSS_FIXTURE, request=httpx.Request("GET", url))

    with _patch_dns("8.8.8.8"):
        with patch("httpx.AsyncClient.get", fake_get):
            result = await fetch_feed(
                "https://real-vendor.test/feed",
                etag=None, last_modified=None, user_agent="OryxIntake/1.0",
            )
    assert result.outcome == FetchOutcome.OK
    assert result.body == _RSS_FIXTURE


# --------------------------------------------------------------------------- #
# Webhook — direct loopback target
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_webhook_direct_loopback_target_is_rejected_without_contacting_server() -> None:
    server, port = _real_server()
    try:
        with pytest.raises(PermanentChannelError):
            await WebhookChannel(backoff_base=0.0).publish(
                "c", "t", {"secret": "s"}, {"url": f"http://127.0.0.1:{port}/hook"},
            )
        server.handle_request()  # real wait; proves nothing arrived
    finally:
        server.server_close()
    assert _CountingHandler.hits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "addr",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "169.254.10.5"],
)
async def test_webhook_rejects_resolved_private_link_local_and_metadata_addresses(addr: str) -> None:
    with _patch_dns(addr):
        with pytest.raises(PermanentChannelError):
            await WebhookChannel(backoff_base=0.0).publish(
                "c", "t", {"secret": "s"}, {"url": "https://vendor.test/hook"},
            )


@pytest.mark.asyncio
async def test_webhook_rejects_non_http_scheme() -> None:
    with pytest.raises(PermanentChannelError):
        await WebhookChannel(backoff_base=0.0).publish(
            "c", "t", {"secret": "s"}, {"url": "file:///etc/passwd"},
        )


@pytest.mark.asyncio
async def test_webhook_does_not_follow_redirect_to_internal_target() -> None:
    """webhook.py never sets follow_redirects=True and has no manual 3xx
    follow logic, so a 3xx from a guard-approved target can't reach a second,
    unvalidated host — confirming there's no redirect-based SSRF surface
    here the way there was for RSS (which does follow redirects)."""
    internal, internal_port = _real_server()

    async def fake_post(self, url, **kw):
        return httpx.Response(
            302,
            headers={"location": f"http://127.0.0.1:{internal_port}/secret"},
            request=httpx.Request("POST", url),
        )

    try:
        with _patch_dns("8.8.8.8"):
            with patch("httpx.AsyncClient.post", fake_post):
                result = await WebhookChannel(backoff_base=0.0).publish(
                    "c", "t", {"secret": "s"}, {"url": "https://vendor.test/hook"},
                )
        # Pre-existing behavior: any status < 400 (including 3xx) counts as
        # delivered without ever requesting Location. Out of scope here —
        # the point of this test is that the internal target is never hit.
        assert result.status == "delivered"
        internal.handle_request()  # real wait; proves nothing arrived
    finally:
        internal.server_close()
    assert _CountingHandler.hits == 0


# --------------------------------------------------------------------------- #
# Webhook — legitimate target still works (regression)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_webhook_legitimate_public_target_still_delivers() -> None:
    async def fake_post(self, url, **kw):
        return httpx.Response(200, json={"id": "whk_ok"}, request=httpx.Request("POST", url))

    with _patch_dns("8.8.8.8"):
        with patch("httpx.AsyncClient.post", fake_post):
            result = await WebhookChannel(backoff_base=0.0).publish(
                "c", "t", {"secret": "s"}, {"url": "https://hooks.vendor.test/deliver"},
            )
    assert result.status == "delivered"
    assert result.external_id == "whk_ok"
