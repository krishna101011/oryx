"""Text sanitization rules for normalized output.

Phase 3 ships a deliberately small surface — the body of an intake item
is stored as raw HTML in `intake_items.payload` and as cleaned text in
`intake_items_normalized.body_text`. Cleaning is:

1. HTML tag removal (no allowlist — we keep text, not structure)
2. Entity decoding
3. Whitespace collapse
4. Zero-width/control-character removal
5. Length cap (defensive — runaway content)

Phase 4 verification operates on the cleaned text; Phase 5 content
generation also pulls from here. Anything richer (link extraction with
anchors, image refs) is captured by the link extractor below.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

_MAX_BODY_CHARS = 50_000

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINE_RUN_RE = re.compile(r"\n{3,}")
_INVISIBLE_RE = re.compile(r"[​-‏ - ­﻿]")
_HREF_RE = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class ExtractedLink:
    url: str
    anchor: str


def normalize_title(raw: str | None) -> str:
    """For fingerprinting: strip emoji, collapse whitespace, lowercase."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", raw)
    s = _INVISIBLE_RE.sub("", s)
    # Strip emoji via category check
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("So"))
    s = _WHITESPACE_RE.sub(" ", s).strip().lower()
    return s


def sanitize_html_to_text(raw_html: str | None) -> str:
    """Cleaned plain-text projection of HTML body. Never returns None."""
    if not raw_html:
        return ""
    s = raw_html.replace("\r\n", "\n").replace("\r", "\n")
    s = _TAG_RE.sub("", s)
    s = html.unescape(s)
    s = _INVISIBLE_RE.sub("", s)
    s = _WHITESPACE_RE.sub(" ", s)
    s = _NEWLINE_RUN_RE.sub("\n\n", s)
    s = s.strip()
    if len(s) > _MAX_BODY_CHARS:
        s = s[:_MAX_BODY_CHARS]
    return s


def extract_links(raw_html: str | None) -> list[ExtractedLink]:
    """Pull href + anchor pairs from raw HTML. Anchor is the cleaned visible text."""
    if not raw_html:
        return []
    out: list[ExtractedLink] = []
    for m in _HREF_RE.finditer(raw_html):
        href = (m.group(1) or "").strip()
        anchor = sanitize_html_to_text(m.group(2) or "")
        if href:
            out.append(ExtractedLink(url=href, anchor=anchor))
    return out
