"""Feed parsing — Atom + RSS 2.0.

feedparser is the standard library for this; we accept the dependency
because re-implementing the full spec (especially Atom + RSS 2.0 + the
seven different "guid" conventions) is a maintenance liability.

The output is a uniform `ParsedItem` shape that the mapper turns into
RawItem. The shape is intentionally small — provider-specific fluff
gets carried through `extra` only if a downstream consumer asks for it.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]

from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)


@dataclass(frozen=True)
class ParsedFeed:
    feed_title: str | None
    feed_url: str | None
    items: list[ParsedItem]


@dataclass(frozen=True)
class ParsedItem:
    external_id: str
    received_at: datetime
    title: str | None
    summary_text: str | None
    content_html: str | None
    primary_link: str | None
    extra: dict[str, Any] = field(default_factory=dict)


def parse_feed(body: bytes, *, fallback_feed_url: str) -> ParsedFeed:
    """Parse raw feed bytes into ParsedFeed.

    Raises ProviderError(PERMANENT) on completely unrecognized payloads.
    feedparser's `bozo` flag is logged but not fatal — many real feeds
    have minor schema deviations.
    """
    fp = feedparser.parse(body)
    if fp.get("bozo") and not fp.get("entries"):
        exc = fp.get("bozo_exception")
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Feed parse failed: {exc}",
        )

    feed_data = fp.get("feed") or {}
    feed_title = feed_data.get("title")
    feed_url = feed_data.get("link") or fallback_feed_url

    items: list[ParsedItem] = []
    for entry in fp.get("entries", []):
        items.append(_entry_to_item(entry, fallback_feed_url=fallback_feed_url))

    return ParsedFeed(feed_title=feed_title, feed_url=feed_url, items=items)


def _entry_to_item(entry: Any, *, fallback_feed_url: str) -> ParsedItem:
    external_id = _pick_external_id(entry, fallback_feed_url=fallback_feed_url)
    received_at = _pick_received_at(entry)
    title = (entry.get("title") or "").strip() or None
    summary_text = (entry.get("summary") or "").strip() or None

    # Prefer content:encoded; fall back to summary HTML if present.
    content_html: str | None = None
    contents = entry.get("content") or []
    if contents:
        # feedparser returns a list of dicts with a `value` field.
        content_html = contents[0].get("value") if contents else None
    if not content_html and summary_text:
        content_html = entry.get("summary")

    link = (entry.get("link") or "").strip() or None

    return ParsedItem(
        external_id=external_id,
        received_at=received_at,
        title=title,
        summary_text=summary_text,
        content_html=content_html,
        primary_link=link,
    )


def _pick_external_id(entry: Any, *, fallback_feed_url: str) -> str:
    # Prefer <guid> when present (RSS 2.0) or <id> (Atom)
    guid = entry.get("id") or entry.get("guid")
    if guid:
        return str(guid)
    # Fallback: deterministic hash of (link, title, pubDate). Stable across
    # repeated fetches so dedupe still works.
    link = entry.get("link") or ""
    title = entry.get("title") or ""
    published = entry.get("published") or entry.get("updated") or ""
    h = hashlib.sha256(
        f"{fallback_feed_url}\x1e{link}\x1e{title}\x1e{published}".encode()
    ).hexdigest()
    return f"sha256:{h}"


def _pick_received_at(entry: Any) -> datetime:
    # feedparser parses dates into a struct_time on `published_parsed` /
    # `updated_parsed`. We prefer published; fall back to updated; final
    # fallback is now (so the item still ingests, with the date_bucket fingerprint).
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                continue
    # Try parsing the raw string as RFC 2822
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except (TypeError, ValueError):
                continue
    return datetime.now(UTC)
