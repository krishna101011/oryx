"""Phase 5 Wave D — channel adapters + credential encryption (unit, no DB).

Covers:
  - AES-256-GCM credential round-trip + that ciphertext leaks no plaintext
  - thread/segment formatting
  - Webhook: a REAL end-to-end signed POST to a local HTTP server (no mocks)
  - Export: a REAL file produced on disk
  - Twitter/LinkedIn/Notion/Newsletter via a faked httpx layer
  - error taxonomy: 401/403 → Permanent, 429/5xx → Transient
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import threading
from typing import ClassVar

import httpx
import pytest


# --------------------------------------------------------------------------- #
# Credential encryption
# --------------------------------------------------------------------------- #
def test_encrypt_decrypt_round_trip() -> None:
    from oryx.core.credential_crypto import decrypt_credentials, encrypt_credentials

    creds = {"api_key": "sk-live-SECRET-123", "person_urn": "urn:li:person:9"}
    ct, iv = encrypt_credentials(creds)
    assert isinstance(ct, bytes) and isinstance(iv, bytes)
    assert len(iv) == 12  # GCM 96-bit nonce
    assert decrypt_credentials(ct, iv) == creds


def test_ciphertext_contains_no_plaintext() -> None:
    from oryx.core.credential_crypto import encrypt_credentials

    secret = "TOP-SECRET-TOKEN-zzz"
    ct, iv = encrypt_credentials({"token": secret})
    assert secret.encode() not in ct
    assert secret.encode() not in iv


def test_distinct_iv_per_call() -> None:
    from oryx.core.credential_crypto import encrypt_credentials

    _, iv1 = encrypt_credentials({"a": "1"})
    _, iv2 = encrypt_credentials({"a": "1"})
    assert iv1 != iv2  # random nonce per call (GCM safety)


def test_tampered_ciphertext_fails() -> None:
    from oryx.core.credential_crypto import decrypt_credentials, encrypt_credentials

    ct, iv = encrypt_credentials({"a": "1"})
    tampered = bytes([ct[0] ^ 0xFF]) + ct[1:]
    with pytest.raises(Exception):
        decrypt_credentials(tampered, iv)


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def test_thread_segments_single_short() -> None:
    from oryx.services.publishing.channels.formatting import thread_segments

    segs = thread_segments("Short and sweet.", 280)
    assert segs == ["Short and sweet."]  # one segment, unnumbered


def test_thread_segments_splits_and_numbers() -> None:
    from oryx.services.publishing.channels.formatting import thread_segments

    text = ". ".join(f"Sentence number {i} here" for i in range(40)) + "."
    segs = thread_segments(text, 80)
    assert len(segs) > 1
    assert all(len(s) <= 80 for s in segs)
    assert segs[0].endswith(f"(1/{len(segs)})")


# --------------------------------------------------------------------------- #
# Webhook — REAL end-to-end against a local HTTP server (no external account)
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
        self.wfile.write(b'{"id": "whk_123"}')

    def log_message(self, *args) -> None:  # silence test server
        pass


@pytest.mark.asyncio
async def test_webhook_real_end_to_end_signed_delivery() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.webhook import WebhookChannel

    _CapturingHandler.received = {}
    server = http.server.HTTPServer(("127.0.0.1", 0), _CapturingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    try:
        ch = WebhookChannel(backoff_base=0.0)
        secret = "shared-secret-xyz"
        # This test is about HMAC signing + real delivery mechanics, not
        # SSRF (127.0.0.1 stands in for a real external endpoint we don't
        # control in tests). The guard itself is covered for real against
        # this same real-local-server pattern in
        # test_ssrf_redirect_and_loopback.py.
        with patch("oryx.services.publishing.channels.webhook._assert_url_safe", lambda url: None):
            result = await ch.publish(
                content="Hello world body",
                draft_title="My Draft",
                credentials={"secret": secret},
                config={"url": f"http://127.0.0.1:{port}/hook"},
            )
    finally:
        thread.join(timeout=5)
        server.server_close()

    assert result.status == "delivered"
    assert result.external_id == "whk_123"  # parsed from the real response

    captured = _CapturingHandler.received
    assert captured, "server received no request"
    # Verify the signature the server received is a correct HMAC over the body.
    ts = int(captured["timestamp"])
    expected = (
        "sha256="
        + hmac.new(
            secret.encode(),
            f"{ts}.".encode() + captured["body"],
            hashlib.sha256,
        ).hexdigest()
    )
    assert captured["signature"] == expected
    assert json.loads(captured["body"])["content"] == "Hello world body"


@pytest.mark.asyncio
async def test_webhook_missing_url_is_permanent() -> None:
    from oryx.services.publishing.channels.base import PermanentChannelError
    from oryx.services.publishing.channels.webhook import WebhookChannel

    with pytest.raises(PermanentChannelError):
        await WebhookChannel().publish("c", "t", {"secret": "s"}, {})


@pytest.mark.asyncio
async def test_webhook_5xx_retries_then_transient() -> None:
    import socket

    from oryx.services.publishing.channels.base import TransientChannelError
    from oryx.services.publishing.channels.webhook import WebhookChannel

    calls = {"n": 0}

    async def fake_post(self, url, **kw):
        calls["n"] += 1
        return httpx.Response(503, text="busy", request=httpx.Request("POST", url))

    from unittest.mock import patch

    def fake_getaddrinfo(host, port, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]

    ch = WebhookChannel(backoff_base=0.0)
    with patch("socket.getaddrinfo", fake_getaddrinfo):
        with patch("httpx.AsyncClient.post", fake_post):
            with pytest.raises(TransientChannelError):
                await ch.publish("c", "t", {"secret": "s"}, {"url": "http://x/y"})
    assert calls["n"] == 3  # 3 internal attempts before giving up


# --------------------------------------------------------------------------- #
# Export — REAL file produced on disk (no external account)
# --------------------------------------------------------------------------- #
def _read_written_file(path: str) -> str:
    """Sync file read — kept out of the async test so the pathlib calls aren't
    flagged by the async-blocking lint (ASYNC240)."""
    from pathlib import Path

    p = Path(path)
    assert p.exists()
    return p.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_export_writes_real_markdown_file(tmp_path) -> None:
    from oryx.services.publishing.channels.export import ExportChannel

    ch = ExportChannel(base_dir=str(tmp_path))
    result = await ch.publish(
        content="Body of the export.",
        draft_title="Quarterly Note",
        credentials={},
        config={},
    )
    assert result.status == "delivered"
    assert result.external_url is not None
    text = _read_written_file(result.external_url)
    assert "# Quarterly Note" in text
    assert "Body of the export." in text


@pytest.mark.asyncio
async def test_export_needs_no_credentials() -> None:
    from oryx.services.publishing.channels.export import ExportChannel

    ch = ExportChannel()
    assert await ch.validate_credentials({}) is True
    assert await ch.health_check({}) is True


# --------------------------------------------------------------------------- #
# Credentialed channels via a faked httpx layer
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_twitter_publish_via_fake_http() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.twitter import TwitterXChannel

    async def fake_post(self, url, **kw):
        return httpx.Response(
            201, json={"data": {"id": "tweet_1"}}, request=httpx.Request("POST", url)
        )

    ch = TwitterXChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await ch.publish("A tweet.", "t", {"access_token": "tok"}, {})
    assert result.status == "delivered"
    assert result.external_id == "tweet_1"
    assert "tweet_1" in result.external_url


@pytest.mark.asyncio
async def test_twitter_401_is_permanent() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.base import PermanentChannelError
    from oryx.services.publishing.channels.twitter import TwitterXChannel

    async def fake_post(self, url, **kw):
        return httpx.Response(401, text="bad", request=httpx.Request("POST", url))

    ch = TwitterXChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        with pytest.raises(PermanentChannelError):
            await ch.publish("A tweet.", "t", {"access_token": "tok"}, {})


@pytest.mark.asyncio
async def test_linkedin_publish_via_fake_http() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.linkedin import LinkedInChannel

    async def fake_post(self, url, **kw):
        return httpx.Response(
            201,
            json={"id": "urn:li:share:99"},
            headers={"x-restli-id": "urn:li:share:99"},
            request=httpx.Request("POST", url),
        )

    ch = LinkedInChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await ch.publish(
            "Post body", "t", {"access_token": "tok", "person_urn": "urn:li:person:1"}, {}
        )
    assert result.status == "delivered"
    assert result.external_id == "urn:li:share:99"


@pytest.mark.asyncio
async def test_notion_publish_via_fake_http() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.notion import NotionChannel

    async def fake_post(self, url, **kw):
        return httpx.Response(
            200,
            json={"id": "page_1", "url": "https://notion.so/page_1"},
            request=httpx.Request("POST", url),
        )

    ch = NotionChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await ch.publish(
            "Line one\nLine two",
            "Title",
            {"integration_token": "tok"},
            {"parent_page_id": "parent_1"},
        )
    assert result.status == "delivered"
    assert result.external_id == "page_1"
    assert result.external_url == "https://notion.so/page_1"


@pytest.mark.asyncio
async def test_notion_missing_parent_is_permanent() -> None:
    from oryx.services.publishing.channels.base import PermanentChannelError
    from oryx.services.publishing.channels.notion import NotionChannel

    with pytest.raises(PermanentChannelError):
        await NotionChannel().publish("c", "t", {"integration_token": "tok"}, {})


@pytest.mark.asyncio
async def test_newsletter_sendgrid_via_fake_http() -> None:
    from unittest.mock import patch

    from oryx.services.publishing.channels.newsletter import NewsletterChannel

    async def fake_post(self, url, **kw):
        return httpx.Response(
            202,
            headers={"x-message-id": "msg_1"},
            request=httpx.Request("POST", url),
        )

    ch = NewsletterChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await ch.publish(
            "Newsletter body",
            "Subject",
            {"api_key": "SG.key", "from_email": "a@b.c"},
            {"provider": "sendgrid", "to": ["reader@x.com"]},
        )
    assert result.status == "delivered"
    assert result.external_id == "msg_1"


@pytest.mark.asyncio
async def test_newsletter_smtp_via_fake_smtplib() -> None:
    from unittest.mock import MagicMock, patch

    from oryx.services.publishing.channels.newsletter import NewsletterChannel

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, u, p):
            sent["login"] = u

        def sendmail(self, frm, to, msg):
            sent["to"] = to

    ch = NewsletterChannel()
    with patch("smtplib.SMTP", FakeSMTP):
        result = await ch.publish(
            "Body",
            "Subj",
            {"host": "smtp.x.com", "username": "u", "password": "p", "from_email": "a@b.c"},
            {"provider": "smtp", "to": ["reader@x.com"]},
        )
    assert result.status == "delivered"
    assert sent["host"] == "smtp.x.com"
    assert sent["to"] == ["reader@x.com"]
    assert result.external_id  # synthesised Message-ID
    _ = MagicMock  # keep import tidy
