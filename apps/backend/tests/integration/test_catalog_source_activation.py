"""Catalog-to-intake activation (RSS catalog redesign, Phase A, 2026-07-22).

Before this wave, POST /intake/sources accepted origin_kind='catalog' +
origin_catalog_key in its request schema, but nothing in the codebase (only
test_credibility_bootstrap.py's isolated fixture) ever exercised it for
real — confirmed via recon: zero real intake_sources rows anywhere trace an
origin_catalog_key back to a real source_catalog vendor key. This is the
first real production test of that path.

Runs only when ORYX_TEST_DB is set (with migrations applied — 0026 seeds
the real catalog rows this file activates).
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> dict[str, str]:
    signup = await client.post("/v1/auth/signup", json={
        "email": f"catalogact+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "CA",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {access}"}


# --- mandatory scenario 1: correct intake_sources row from a real catalog entry ---


@pytest.mark.asyncio
async def test_catalog_activation_creates_a_real_intake_source_from_the_catalog_row(
    app,
) -> None:
    """Enabling the real 'cointelegraph' catalog entry (migration 0026)
    creates a genuine intake_sources row: origin_kind='catalog',
    origin_catalog_key set, kind forced to 'rss', name and feed_url both
    coming from the real catalog row — not from anything the client sent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "ignored — server derives this for catalog activations",
            "kind": "manual",  # also ignored/overridden for the catalog path
            "origin_kind": "catalog",
            "origin_catalog_key": "cointelegraph",
            "config": {},
        })
        assert res.status_code == 200, res.text
        data = res.json()["data"]
        assert data["name"] == "Cointelegraph"
        assert data["kind"] == "rss"
        assert data["originKind"] == "catalog"
        assert data["originCatalogKey"] == "cointelegraph"
        assert data["config"]["feed_url"] == "https://cointelegraph.com/rss"
        assert data["enabled"] is True
        assert data["health"] == "healthy"


@pytest.mark.asyncio
async def test_catalog_activation_ignores_client_supplied_feed_url(app) -> None:
    """A client cannot smuggle an arbitrary feed_url in by claiming a real
    origin_catalog_key — the server always derives feed_url from the real
    catalog row, proving the integrity fix recon called for."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "x",
            "kind": "rss",
            "origin_kind": "catalog",
            "origin_catalog_key": "decrypt",
            "config": {"feed_url": "https://malicious.example/not-decrypt.xml"},
        })
        assert res.status_code == 200, res.text
        assert res.json()["data"]["config"]["feed_url"] == "https://decrypt.co/feed"


@pytest.mark.asyncio
async def test_catalog_activation_preserves_client_cadence_override(app) -> None:
    """Non-feed_url config (fetch_interval_minutes) still passes through —
    catalog-backed sources "inherit feed_url and only edit polling cadence"
    per providers/rss/config_schema.py's own documented intent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "x",
            "kind": "rss",
            "origin_kind": "catalog",
            "origin_catalog_key": "yahoo_finance",
            "config": {"fetch_interval_minutes": 60},
        })
        assert res.status_code == 200, res.text
        config = res.json()["data"]["config"]
        assert config["feed_url"] == "https://finance.yahoo.com/news/rssindex"
        assert config["fetch_interval_minutes"] == 60


@pytest.mark.asyncio
async def test_catalog_activation_requires_origin_catalog_key(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "x", "kind": "rss", "origin_kind": "catalog", "config": {},
        })
        assert res.status_code == 422, res.text
        assert res.json()["error"]["details"]["reason"] == "missing_origin_catalog_key"


@pytest.mark.asyncio
async def test_catalog_activation_404s_for_an_unknown_catalog_key(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "x", "kind": "rss", "origin_kind": "catalog",
            "origin_catalog_key": "not-a-real-key", "config": {},
        })
        assert res.status_code == 404, res.text


# --- mandatory scenario 2: the existing custom RSS path is unaffected ---


@pytest.mark.asyncio
async def test_custom_rss_creation_is_unaffected_by_the_catalog_activation_path(
    app,
) -> None:
    """Regression: origin_kind='custom' must behave EXACTLY as before —
    client-supplied name/kind/config all pass through untouched, no catalog
    lookup happens at all."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        res = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "My Own Feed",
            "kind": "rss",
            "origin_kind": "custom",
            "config": {"feed_url": "https://example.test/my-own-feed.xml"},
        })
        assert res.status_code == 200, res.text
        data = res.json()["data"]
        assert data["name"] == "My Own Feed"
        assert data["originKind"] == "custom"
        assert data["originCatalogKey"] is None
        assert data["config"]["feed_url"] == "https://example.test/my-own-feed.xml"


# --- mandatory scenario 3: the real catalog feed URLs are ACTUALLY reachable ---


REAL_CATALOG_FEED_URLS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
    "the_block": "https://www.theblock.co/rss.xml",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "investing_company_news": "https://www.investing.com/rss/news_356.rss",
    "investing_stock_market_news": "https://www.investing.com/rss/news_25.rss",
    "investing_earnings": "https://www.investing.com/rss/news_1063.rss",
}


@pytest.mark.requires_network
@pytest.mark.asyncio
@pytest.mark.parametrize("key,url", sorted(REAL_CATALOG_FEED_URLS.items()))
async def test_real_catalog_feed_urls_are_actually_reachable(key: str, url: str) -> None:
    """A LIVE connectivity check against the real internet — not a URL
    format check. Uses the exact real fetch_feed the production sync path
    calls, so this proves the same code that will run in the scheduler can
    really reach each vendor and get back real, non-empty RSS content."""
    from oryx.services.intake.providers.rss.client import FetchOutcome, fetch_feed

    result = await fetch_feed(
        url, etag=None, last_modified=None,
        user_agent="OryxIntake/1.0 (+https://oryx.app)",
    )
    assert result.outcome == FetchOutcome.OK, f"{key} ({url}) did not return OK"
    assert result.body is not None and len(result.body) > 0
    assert b"<rss" in result.body[:200].lower() or b"<feed" in result.body[:200].lower(), (
        f"{key} ({url}) response body doesn't look like RSS/Atom XML"
    )


# --- Phase 3: real end-to-end ingestion — not just a row, real items ---


@pytest.mark.requires_network
@pytest.mark.asyncio
async def test_catalog_activated_source_ingests_real_items_within_one_real_sync(
    app, sm,
) -> None:
    """The actual proof this wave exists to produce: enable a real catalog
    entry over the real API, run ONE real sync cycle through the exact
    production SourceSyncRunner (the same class the scheduler uses), fetch
    the real cointelegraph.com/rss feed over the real internet, and confirm
    real intake_items rows landed with real, non-empty content — not a
    mocked provider, not just a created row."""
    from sqlalchemy import select

    from oryx.core.models import IntakeItem, IntakeItemNormalized
    from oryx.services.intake.sync_runner import SourceSyncRunner, SyncOutcome

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)
        created = await client.post("/v1/intake/sources", headers=headers, json={
            "name": "ignored",
            "kind": "manual",
            "origin_kind": "catalog",
            "origin_catalog_key": "cointelegraph",
            "config": {},
        })
        assert created.status_code == 200, created.text
        source_id = uuid.UUID(created.json()["data"]["id"])

    runner = SourceSyncRunner(sm)
    outcome = await runner.sync_source(source_id)
    assert outcome == SyncOutcome.COMPLETED, (
        "real sync against the live cointelegraph.com/rss feed did not complete"
    )

    async with sm() as session:
        rows = (
            await session.execute(
                select(IntakeItem, IntakeItemNormalized)
                .join(
                    IntakeItemNormalized,
                    IntakeItemNormalized.intake_item_id == IntakeItem.id,
                )
                .where(IntakeItem.intake_source_id == source_id)
            )
        ).all()

    assert len(rows) > 0, "real sync completed but ingested zero real items"
    for item, normalized in rows:
        assert item.provider_name == "rss"
        assert item.payload.get("primary_link", "").startswith("https://cointelegraph.com")
        assert normalized.subject, "a real feed item must have a real headline"
        assert len(normalized.subject) > 0
