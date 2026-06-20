"""RSS provider — config validation, parsing, mapping, cursor advancement.

Tests against a fixture; no real network. Network behavior is exercised
by Wave G integration tests.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from oryx.services.intake.providers.base import (
    IntakeSourceKind,
    ValidationStatus,
)
from oryx.services.intake.providers.rss.client import (
    FetchOutcome,
    FetchResult,
)
from oryx.services.intake.providers.rss.mapper import parsed_item_to_raw
from oryx.services.intake.providers.rss.parser import parse_feed
from oryx.services.intake.providers.rss.sync import (
    RssProvider,
    cursor_from_report,
)

# ----------------------------- fixtures -----------------------------

_RSS_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.test/feed</link>
    <item>
      <guid>item-1-guid</guid>
      <title>Daily Macro Brief</title>
      <link>https://example.test/article-1?utm_source=feed</link>
      <pubDate>Sat, 06 Jun 2026 09:00:00 +0000</pubDate>
      <description>&lt;p&gt;Hello&amp;nbsp;<b>world</b>&lt;/p&gt;</description>
    </item>
    <item>
      <guid>item-2-guid</guid>
      <title>Crypto Weekly</title>
      <link>https://example.test/article-2</link>
      <pubDate>Sat, 06 Jun 2026 10:30:00 +0000</pubDate>
      <description>Body for item 2</description>
    </item>
  </channel>
</rss>
"""

_ATOM_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test</title>
  <link href="https://atom.test/feed"/>
  <entry>
    <id>urn:atom:item-1</id>
    <title>Atom Item</title>
    <link href="https://atom.test/a-1"/>
    <published>2026-06-06T09:00:00Z</published>
    <content type="html">&lt;p&gt;Atom body&lt;/p&gt;</content>
  </entry>
</feed>
"""


# ----------------------------- config -------------------------------

@pytest.mark.asyncio
async def test_validate_config_accepts_minimal_valid_input() -> None:
    p = RssProvider()
    result = await p.validate_config({"feed_url": "https://example.test/feed"})
    assert result.status == ValidationStatus.OK


@pytest.mark.asyncio
async def test_validate_config_rejects_missing_url() -> None:
    p = RssProvider()
    result = await p.validate_config({})
    assert result.status == ValidationStatus.INVALID


@pytest.mark.asyncio
async def test_validate_config_rejects_below_minimum_interval() -> None:
    p = RssProvider()
    result = await p.validate_config(
        {"feed_url": "https://example.test/feed", "fetch_interval_minutes": 1}
    )
    assert result.status == ValidationStatus.INVALID


# ----------------------------- parsing ------------------------------

def test_parse_rss_2_0_yields_two_items() -> None:
    feed = parse_feed(_RSS_FIXTURE, fallback_feed_url="https://example.test/feed")
    assert feed.feed_title == "Test Feed"
    assert len(feed.items) == 2
    assert feed.items[0].external_id == "item-1-guid"
    assert feed.items[0].title == "Daily Macro Brief"
    assert feed.items[0].primary_link is not None


def test_parse_atom_yields_one_item() -> None:
    feed = parse_feed(_ATOM_FIXTURE, fallback_feed_url="https://atom.test/feed")
    assert "Atom" in (feed.feed_title or "")
    assert len(feed.items) == 1
    assert feed.items[0].external_id == "urn:atom:item-1"


def test_received_at_parsed_from_pubdate() -> None:
    feed = parse_feed(_RSS_FIXTURE, fallback_feed_url="https://x")
    received = feed.items[0].received_at
    assert isinstance(received, datetime)
    assert received.year == 2026 and received.month == 6 and received.day == 6


# ----------------------------- mapping ------------------------------

def test_mapper_produces_raw_item_with_canonical_link_and_anchor() -> None:
    feed = parse_feed(_RSS_FIXTURE, fallback_feed_url="https://x")
    raw = parsed_item_to_raw(feed.items[0], feed_title=feed.feed_title)
    assert raw.external_id == "item-1-guid"
    assert raw.sender == "Test Feed"
    assert raw.subject == "Daily Macro Brief"
    assert raw.primary_link is not None
    assert raw.links[0]["url"].startswith("https://example.test/article-1")


# --------------------------- sync loop ------------------------------

class _FakeAsyncFetch:
    """Shape-compatible replacement for fetch_feed (async function)."""

    def __init__(self, result: FetchResult) -> None:
        self.calls: list[tuple[str, str | None, str | None]] = []
        self._result = result

    async def __call__(self, url: str, **kw: Any) -> FetchResult:
        self.calls.append((url, kw.get("etag"), kw.get("last_modified")))
        return self._result


@pytest.mark.asyncio
async def test_sync_yields_items_on_200() -> None:
    fake = _FakeAsyncFetch(
        FetchResult(
            outcome=FetchOutcome.OK,
            body=_RSS_FIXTURE,
            etag='"abc123"',
            last_modified="Sat, 06 Jun 2026 09:00:00 GMT",
            content_type="application/rss+xml",
            final_url="https://example.test/feed",
        )
    )
    p = RssProvider()
    with patch("oryx.services.intake.providers.rss.sync.fetch_feed", fake):
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config={"feed_url": "https://example.test/feed"},
        ):
            items.append(raw)
    assert len(items) == 2
    assert p.last_report is not None
    assert p.last_report.items_yielded == 2
    assert p.last_report.new_etag == '"abc123"'


@pytest.mark.asyncio
async def test_sync_yields_nothing_on_304_and_keeps_cursor() -> None:
    fake = _FakeAsyncFetch(
        FetchResult(
            outcome=FetchOutcome.NOT_MODIFIED,
            body=None,
            etag=None,
            last_modified=None,
            content_type=None,
            final_url=None,
        )
    )
    p = RssProvider()
    with patch("oryx.services.intake.providers.rss.sync.fetch_feed", fake):
        async for _ in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config={"feed_url": "https://x.test/feed"},
        ):
            pytest.fail("304 should yield nothing")
    assert p.last_report is not None
    assert p.last_report.items_yielded == 0


@pytest.mark.asyncio
async def test_sync_surfaces_301_for_caller_to_persist_cr10() -> None:
    fake = _FakeAsyncFetch(
        FetchResult(
            outcome=FetchOutcome.REDIRECT_PERMANENT,
            body=None,
            etag=None,
            last_modified=None,
            content_type=None,
            final_url="https://new.example.test/feed",
        )
    )
    p = RssProvider()
    with patch("oryx.services.intake.providers.rss.sync.fetch_feed", fake):
        async for _ in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config={"feed_url": "https://example.test/feed"},
        ):
            pytest.fail("301 should yield nothing")
    assert p.last_report is not None
    assert p.last_report.permanent_redirect_to == "https://new.example.test/feed"


@pytest.mark.asyncio
async def test_cursor_built_from_etag_and_last_modified() -> None:
    fake = _FakeAsyncFetch(
        FetchResult(
            outcome=FetchOutcome.OK,
            body=_RSS_FIXTURE,
            etag='"new"',
            last_modified="Sun, 07 Jun 2026 09:00:00 GMT",
            content_type="application/rss+xml",
            final_url="https://example.test/feed",
        )
    )
    p = RssProvider()
    with patch("oryx.services.intake.providers.rss.sync.fetch_feed", fake):
        async for _ in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config={"feed_url": "https://example.test/feed"},
        ):
            pass
    cursor = cursor_from_report(p.last_report)  # type: ignore[arg-type]
    assert cursor == {
        "etag": '"new"',
        "last_modified": "Sun, 07 Jun 2026 09:00:00 GMT",
    }


@pytest.mark.asyncio
async def test_sync_forwards_existing_cursor_to_fetch() -> None:
    fake = _FakeAsyncFetch(
        FetchResult(
            outcome=FetchOutcome.NOT_MODIFIED,
            body=None, etag=None, last_modified=None,
            content_type=None, final_url=None,
        )
    )
    from oryx.services.intake.providers.base import SyncCursor
    cursor = SyncCursor(value={"etag": '"old"', "last_modified": "x"})
    p = RssProvider()
    with patch("oryx.services.intake.providers.rss.sync.fetch_feed", fake):
        async for _ in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=cursor,
            config={"feed_url": "https://example.test/feed"},
        ):
            pass
    assert fake.calls[0][1] == '"old"'
    assert fake.calls[0][2] == "x"


def test_provider_metadata_locked() -> None:
    """RssProvider.name and .kind are part of the wire contract — guard them."""
    p = RssProvider()
    assert p.name == "rss"
    assert p.kind == IntakeSourceKind.RSS
