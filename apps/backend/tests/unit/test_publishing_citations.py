"""Phase 5 post-freeze — citation provenance patch (unit, no DB).

Covers the channel-proportional citation footer and the webhook's separate
structured citations field:
  - twitter_x: footer omitted (not truncated) at the exact 280-char boundary
  - linkedin / email_newsletter: capped at 3 + an overflow "more sources" line
  - notion / export: ALL citations, uncapped, with epistemic type
  - webhook: citations arrive as a distinct JSON field, never mixed into content
    (asserted on the REAL payload a local HTTP server receives — Wave D pattern)
  - zero-citation draft: graceful for both a prose channel and webhook
  - confidence tiers reuse the canonical band thresholds (no second tier system)
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import threading
from typing import ClassVar

import pytest

from oryx.services.publishing.citations import (
    CitationSummary,
    _confidence_tier,
    format_citation_footer,
)
from oryx.shared.types import CONFIDENCE_BAND_THRESHOLDS


def _cite(headline: str, tier: str = "high", etype: str = "fact") -> CitationSummary:
    return CitationSummary(headline=headline, confidence_tier=tier, epistemic_type=etype)


# --------------------------------------------------------------------------- #
# Confidence tier reuse (NOT a second tier system)
# --------------------------------------------------------------------------- #
def test_confidence_tier_reuses_canonical_band_thresholds() -> None:
    # Exactly the labels/boundaries of CONFIDENCE_BAND_THRESHOLDS (scoring.ts).
    assert _confidence_tier(None) == "unscored"
    assert _confidence_tier(0.90) == "high"
    assert _confidence_tier(0.75) == "high"  # inclusive lower bound
    assert _confidence_tier(0.60) == "moderate"
    assert _confidence_tier(0.30) == "low"
    assert _confidence_tier(0.10) == "minimal"
    # Drift guard: the thresholds are the shared constant, not hard-coded here.
    assert CONFIDENCE_BAND_THRESHOLDS[0] == ("high", 0.75)


# --------------------------------------------------------------------------- #
# Twitter — exact 280 boundary: omit, never truncate
# --------------------------------------------------------------------------- #
def test_twitter_footer_at_280_boundary_omit_vs_keep() -> None:
    cites = [_cite("h1"), _cite("h2"), _cite("h3")]  # N = 3
    footer = "\n\n— 3 verified sources"

    # Final tweet len + footer == 280 exactly → fits, footer kept verbatim.
    content_fit = "A" * (280 - len(footer))
    assert format_citation_footer(cites, "twitter_x", content=content_fit) == footer

    # One char more → 281 > 280 → footer omitted entirely (no truncation).
    content_over = "A" * (280 - len(footer) + 1)
    assert format_citation_footer(cites, "twitter_x", content=content_over) == ""


def test_twitter_footer_singular_vs_plural() -> None:
    assert format_citation_footer([_cite("h")], "twitter_x", content="x") == (
        "\n\n— 1 verified source"
    )
    assert format_citation_footer(
        [_cite("a"), _cite("b")], "twitter_x", content="x"
    ) == "\n\n— 2 verified sources"


# --------------------------------------------------------------------------- #
# LinkedIn / Newsletter — capped at 3 + overflow line
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("channel", ["linkedin", "email_newsletter"])
def test_prose_list_caps_at_three_with_overflow(channel) -> None:
    cites = [_cite(f"Headline {i}", tier="moderate") for i in range(5)]  # N = 5
    footer = format_citation_footer(cites, channel)

    assert footer.startswith("\n\nSources:\n")
    assert footer.count("•") == 3  # only the first three are shown in full
    assert "Headline 0 (moderate)" in footer
    assert "Headline 3" not in footer  # 4th+ are folded into the overflow line
    assert "+ 2 more verified source(s)" in footer


@pytest.mark.parametrize("channel", ["linkedin", "email_newsletter"])
def test_prose_list_no_overflow_when_three_or_fewer(channel) -> None:
    cites = [_cite("Only one")]
    footer = format_citation_footer(cites, channel)
    assert footer == "\n\nSources:\n• Only one (high)"
    assert "more verified source" not in footer


# --------------------------------------------------------------------------- #
# Notion / Export — ALL citations, uncapped, with epistemic type
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("channel", ["notion", "export"])
def test_notion_export_includes_all_citations_uncapped(channel) -> None:
    cites = [_cite(f"Headline {i}", tier="high", etype="claim") for i in range(7)]
    footer = format_citation_footer(cites, channel)

    assert footer.startswith("\n\n## Sources\n")
    # Every one of the seven appears — nothing capped or summarised.
    assert footer.count("- ") == 7
    for i in range(7):
        assert f"- Headline {i} (high, claim)" in footer
    assert "more verified source" not in footer


# --------------------------------------------------------------------------- #
# Zero citations — graceful for prose AND webhook
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("channel", ["twitter_x", "linkedin", "email_newsletter", "notion", "export"])
def test_zero_citations_prose_returns_empty_footer(channel) -> None:
    assert format_citation_footer([], channel, content="some body") == ""
    # No broken/empty "Sources:" heading is ever produced.
    assert "Sources" not in format_citation_footer([], channel, content="x")


# --------------------------------------------------------------------------- #
# Webhook — citations as a SEPARATE JSON field on the real received payload
# --------------------------------------------------------------------------- #
class _CapturingHandler(http.server.BaseHTTPRequestHandler):
    received: ClassVar[dict] = {}

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).received = {
            "body": body,
            "signature": self.headers.get("X-Oryx-Signature"),
            "timestamp": self.headers.get("X-Oryx-Timestamp"),
        }
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"id": "whk_1"}')

    def log_message(self, *args) -> None:  # silence test server
        pass


async def _post_to_local_server(content: str, citations) -> dict:
    """Run WebhookChannel.publish against a real local server; return the parsed
    JSON body the server received."""
    from unittest.mock import patch

    from oryx.services.publishing.channels.webhook import WebhookChannel

    _CapturingHandler.received = {}
    server = http.server.HTTPServer(("127.0.0.1", 0), _CapturingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        ch = WebhookChannel(backoff_base=0.0)
        # This test is about the citations payload shape, not SSRF (127.0.0.1
        # stands in for a real external endpoint we don't control in tests).
        # The guard itself is proven for real in test_ssrf_redirect_and_loopback.py.
        with patch("oryx.services.publishing.channels.webhook._assert_url_safe", lambda url: None):
            result = await ch.publish(
                content=content,
                draft_title="My Draft",
                credentials={"secret": "shared-secret"},
                config={"url": f"http://127.0.0.1:{port}/hook"},
                citations=citations,
            )
    finally:
        thread.join(timeout=5)
        server.server_close()

    assert result.status == "delivered"
    captured = _CapturingHandler.received
    assert captured, "server received no request"
    # Signature still verifies over the (now citation-bearing) body.
    ts = int(captured["timestamp"])
    expected = (
        "sha256="
        + hmac.new(
            b"shared-secret", f"{ts}.".encode() + captured["body"], hashlib.sha256
        ).hexdigest()
    )
    assert captured["signature"] == expected
    return json.loads(captured["body"])


@pytest.mark.asyncio
async def test_webhook_citations_are_a_separate_field_never_in_content() -> None:
    cites = [
        _cite("First source", tier="high", etype="fact"),
        _cite("Second source", tier="moderate", etype="claim"),
    ]
    payload = await _post_to_local_server("Body content only", cites)

    # Content is exactly the draft body — no "Sources" footer mixed in.
    assert payload["content"] == "Body content only"
    assert "Sources" not in payload["content"]
    assert "First source" not in payload["content"]

    # Citations are their own structured array with camelCase keys.
    assert payload["citations"] == [
        {"headline": "First source", "confidenceTier": "high", "epistemicType": "fact"},
        {
            "headline": "Second source",
            "confidenceTier": "moderate",
            "epistemicType": "claim",
        },
    ]


@pytest.mark.asyncio
async def test_webhook_zero_citations_sends_empty_array() -> None:
    payload = await _post_to_local_server("Body", [])
    assert payload["content"] == "Body"
    assert payload["citations"] == []  # empty array, never a crash or omission


@pytest.mark.asyncio
async def test_webhook_citations_default_none_is_backward_compatible() -> None:
    """Pre-patch call sites pass no citations → no citations key at all."""
    from unittest.mock import patch

    from oryx.services.publishing.channels.webhook import WebhookChannel

    _CapturingHandler.received = {}
    server = http.server.HTTPServer(("127.0.0.1", 0), _CapturingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        ch = WebhookChannel(backoff_base=0.0)
        with patch("oryx.services.publishing.channels.webhook._assert_url_safe", lambda url: None):
            result = await ch.publish(
                "Body", "Title", {"secret": "s"}, {"url": f"http://127.0.0.1:{port}/h"}
            )
    finally:
        thread.join(timeout=5)
        server.server_close()

    assert result.status == "delivered"
    payload = json.loads(_CapturingHandler.received["body"])
    assert "citations" not in payload
