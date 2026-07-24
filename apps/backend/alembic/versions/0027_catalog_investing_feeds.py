"""Source catalog: add real Investing.com topic feeds.

Revision ID: 0027_catalog_investing_feeds
Revises: 0026_catalog_real_feeds
Create Date: 2026-07-23

Follow-up to 0026's real-feed-URL-only standard. Recon on the deferred
Investing.com catalog question found 15 real Investing.com-origin
intake_sources rows already live in production data (workspace
23a91c1d-b50a-4d0a-a241-a84e67b9bd8b), spanning forex, commodities,
economy, crypto-opinion, and stock topics — several overlapping (four
separate forex variants, two macro variants) or duplicated (two rows
both named "Investing.com Breaking News Headlines", one soft-deleted).

Of those, three represent genuinely distinct, non-overlapping topic
areas worth a catalog entry, matching the same standard as 0026 (a
real, live-checked feed URL, not a homepage guess):

  - Investing.com Company News (per-company news, distinct from broad
    market headlines) — https://www.investing.com/rss/news_356.rss
  - Investing.com Stock Market News (broad market headlines) —
    https://www.investing.com/rss/news_25.rss
  - Investing.com Earnings Reports & Whispers (earnings-specific,
    including pre-report "whisper" estimates) —
    https://www.investing.com/rss/news_1063.rss

All three feed URLs were live-checked (HTTP 200, application/rss+xml)
immediately before this migration was written. All three are equity/
company financial content, so `focus='markets'` fits them honestly —
this migration does NOT introduce a new 'news' focus value; nothing
here is outside the existing markets/crypto split.

Not added: the four forex variants and two macro variants (too
overlapping with each other to justify separate catalog rows without a
finer-grained taxonomy than `focus` currently supports), Central Bank
Speeches and Commodities News (real but narrower/niche than the three
above), and Crypto Opinion & Analysis (opinion content, weaker
editorial standing than the reported-news bar this catalog holds).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0027_catalog_investing_feeds"
down_revision = "0026_catalog_real_feeds"
branch_labels = None
depends_on = None

_FOCUS_ENUM = sa.Enum("markets", "crypto", "both", name="focus", create_type=False)

_NEW_KEYS = ("investing_company_news", "investing_stock_market_news", "investing_earnings")


def upgrade() -> None:
    source_catalog = sa.table(
        "source_catalog",
        sa.column("key", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("focus", _FOCUS_ENUM),
        sa.column("editorial_confidence", sa.Integer()),
    )
    op.bulk_insert(
        source_catalog,
        [
            {
                "key": "investing_company_news",
                "name": "Investing.com Company News",
                "url": "https://www.investing.com/rss/news_356.rss",
                "focus": "markets",
                "editorial_confidence": 78,
            },
            {
                "key": "investing_stock_market_news",
                "name": "Investing.com Stock Market News",
                "url": "https://www.investing.com/rss/news_25.rss",
                "focus": "markets",
                "editorial_confidence": 80,
            },
            {
                "key": "investing_earnings",
                "name": "Investing.com Earnings Reports & Whispers",
                "url": "https://www.investing.com/rss/news_1063.rss",
                "focus": "markets",
                "editorial_confidence": 76,
            },
        ],
    )


def downgrade() -> None:
    source_catalog = sa.table("source_catalog", sa.column("key", sa.Text()))
    op.execute(source_catalog.delete().where(source_catalog.c.key.in_(_NEW_KEYS)))
