"""Gmail message (v1 JSON) → RawItem.

Pure transformation. No IO. No business logic.

We extract from `format=full` responses:
  external_id        = message id
  received_at        = internalDate (epoch ms)
  sender             = From header (full "Name <addr>")
  subject            = Subject header
  body_text          = decoded text/plain part if present
  body_html          = decoded text/html part if present
  links              = derived by the normalizer from body_html
  label_ids          = message.labelIds (Gmail label assignments)
  thread_id          = message.threadId
  raw_headers_hash   = sha256 of the canonical header block (forensics)
  payload            = the raw vendor JSON (stored verbatim in intake_items)
"""
from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from typing import Any

from anant.services.intake.providers.base import RawItem


def gmail_message_to_raw(message: dict[str, Any]) -> RawItem:
    payload = message.get("payload") or {}
    headers = _headers_dict(payload.get("headers") or [])

    sender = headers.get("from")
    subject = headers.get("subject")
    received_at = _internal_date_to_dt(message.get("internalDate"))

    body_text, body_html = _extract_bodies(payload)
    raw_headers_hash = _canonical_header_hash(payload.get("headers") or [])

    extra = {
        "label_ids": list(message.get("labelIds") or []),
        "thread_id": message.get("threadId"),
        "raw_headers_hash": raw_headers_hash,
        "history_id": message.get("historyId"),
    }

    return RawItem(
        external_id=message["id"],
        received_at=received_at,
        sender=sender,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        links=[],  # the normalizer extracts these from body_html
        payload={**message, **extra},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    """Lowercase keys → first value. Gmail returns headers as a list of dicts."""
    out: dict[str, str] = {}
    for h in headers:
        name = (h.get("name") or "").lower()
        value = h.get("value") or ""
        # First wins — RFC 5322 allows duplicates; we keep the first.
        if name and name not in out:
            out[name] = value
    return out


def _internal_date_to_dt(epoch_ms: Any) -> datetime:
    try:
        ms = int(epoch_ms)
    except (TypeError, ValueError):
        return datetime.now(UTC)
    return datetime.fromtimestamp(ms / 1000.0, tz=UTC)


def _extract_bodies(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Walk MIME parts; return (text/plain, text/html) decoded as utf-8."""
    text: str | None = None
    html: str | None = None

    def visit(node: dict[str, Any]) -> None:
        nonlocal text, html
        mime = node.get("mimeType") or ""
        body = node.get("body") or {}
        data = body.get("data")
        if data and mime.startswith("text/"):
            decoded = _decode_b64url(data)
            if mime == "text/plain" and text is None:
                text = decoded
            elif mime == "text/html" and html is None:
                html = decoded
        for child in node.get("parts") or []:
            visit(child)

    visit(payload)
    return text, html


def _decode_b64url(s: str) -> str:
    # Gmail uses URL-safe base64 without padding.
    pad = "=" * (-len(s) % 4)
    raw = base64.urlsafe_b64decode(s + pad)
    try:
        return raw.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _canonical_header_hash(headers: list[dict[str, str]]) -> str:
    """Stable hash of the headers — for forensics + dedupe diagnostics.

    Sorted by (lowercased-name, value) for determinism. We do NOT hash
    server-added headers (Received, X-Gmail-*) since they vary between
    fetches of the same message.
    """
    skip_prefixes = ("received", "x-gmail-", "x-google-", "delivered-to")
    rows: list[str] = []
    for h in headers:
        name = (h.get("name") or "").lower()
        value = (h.get("value") or "").strip()
        if any(name.startswith(p) for p in skip_prefixes):
            continue
        rows.append(f"{name}:{value}")
    rows.sort()
    return hashlib.sha256("\x1e".join(rows).encode("utf-8")).hexdigest()
