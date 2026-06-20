"""Stateless raw → normalized projection.

Input:  RawItem (provider-shaped, see providers/base.py)
Output: NormalizedItem (storage-shaped; what goes into intake_items_normalized)

This module has no IO. All side effects are the caller's responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from oryx.services.normalization.text_sanitizer import (
    extract_links,
    sanitize_html_to_text,
)
from oryx.services.normalization.url_canonicalizer import (
    canonicalize_url,
    extract_domain,
)
from oryx.services.normalization.version import NORMALIZER_VERSION


@dataclass(frozen=True)
class NormalizedItem:
    sender_domain: str | None
    sender_label: str | None
    subject: str | None
    body_text: str
    links: list[dict[str, str]]  # JSON-friendly
    metadata: dict[str, Any] = field(default_factory=dict)
    normalizer_version: int = NORMALIZER_VERSION


def normalize_raw_item(raw_payload: dict[str, Any]) -> NormalizedItem:
    """Apply Phase 3 Batch 1 normalization rules.

    The shape of `raw_payload` is documented in providers/base.py::RawItem.
    Fields are read by name; unknown fields are ignored.
    """
    sender_raw: str = (raw_payload.get("sender") or "").strip()
    sender_domain = extract_domain(sender_raw) if sender_raw else None
    sender_label = sender_raw or None

    subject_raw = raw_payload.get("subject")
    subject = (subject_raw or "").strip() or None

    body_html: str = raw_payload.get("body_html") or raw_payload.get("body_text") or ""
    body_text = sanitize_html_to_text(body_html)

    links_input = raw_payload.get("links")
    links: list[dict[str, str]] = []
    if isinstance(links_input, list):
        for entry in links_input:
            if isinstance(entry, dict):
                url = entry.get("url") or entry.get("href")
                anchor = entry.get("anchor") or entry.get("text") or ""
                if url:
                    links.append(
                        {"url": canonicalize_url(url), "anchor": str(anchor)}
                    )
    if not links and body_html:
        for ln in extract_links(body_html):
            links.append({"url": canonicalize_url(ln.url), "anchor": ln.anchor})

    metadata: dict[str, Any] = {}
    if (label_ids := raw_payload.get("label_ids")) is not None:
        metadata["label_ids"] = list(label_ids)
    if (thread_id := raw_payload.get("thread_id")) is not None:
        metadata["thread_id"] = thread_id
    if (headers_hash := raw_payload.get("raw_headers_hash")) is not None:
        metadata["raw_headers_hash"] = headers_hash

    return NormalizedItem(
        sender_domain=sender_domain,
        sender_label=sender_label,
        subject=subject,
        body_text=body_text,
        links=links,
        metadata=metadata,
    )
