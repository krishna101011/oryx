"""Source catalog: replace decorative majors with real, working RSS feeds.

Revision ID: 0026_catalog_real_feeds
Revises: 0025_preferences_theme_mode
Create Date: 2026-07-22

Recon (source-governance follow-up wave) found that migration 0001's
`source_catalog` seed used vendor HOMEPAGE urls (bloomberg.com, ft.com,
reuters.com, wsj.com) — none of them a working feed endpoint, so none could
ever be activated as a real intake source. This migration:

  - Removes the four homepage-only majors (bloomberg, ft, reuters, wsj).
    Their `workspace_sources` toggle rows are deleted first (no ON DELETE
    clause on that FK) — confirmed via recon that every real account
    referencing them only ever received a decorative, non-functional entry,
    so nothing functional is lost.
  - Updates coindesk/decrypt to their real, confirmed public RSS feed URLs
    (previously also homepage-only).
  - Adds cointelegraph (crypto) and yahoo_finance (markets) as new real
    entries — yahoo_finance's feed URL is not a guess: it is copied from a
    real, already-syncing custom intake_sources row found in production
    data during recon.
  - `the_block` is deliberately left untouched: recon did not turn up a
    confirmed working feed URL for it, so it stays decorative pending a
    follow-up rather than being guessed at here.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0026_catalog_real_feeds"
down_revision = "0025_preferences_theme_mode"
branch_labels = None
depends_on = None

_REMOVED_KEYS = ("bloomberg", "ft", "reuters", "wsj")

_FOCUS_ENUM = sa.Enum("markets", "crypto", "both", name="focus", create_type=False)


def upgrade() -> None:
    workspace_sources = sa.table(
        "workspace_sources", sa.column("source_key", sa.Text())
    )
    op.execute(
        workspace_sources.delete().where(
            workspace_sources.c.source_key.in_(_REMOVED_KEYS)
        )
    )

    source_catalog = sa.table(
        "source_catalog",
        sa.column("key", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("focus", _FOCUS_ENUM),
        sa.column("editorial_confidence", sa.Integer()),
    )
    op.execute(source_catalog.delete().where(source_catalog.c.key.in_(_REMOVED_KEYS)))

    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "coindesk")
        .values(url="https://www.coindesk.com/arc/outboundfeeds/rss/")
    )
    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "decrypt")
        .values(url="https://decrypt.co/feed")
    )

    op.bulk_insert(
        source_catalog,
        [
            {
                "key": "cointelegraph",
                "name": "Cointelegraph",
                "url": "https://cointelegraph.com/rss",
                "focus": "crypto",
                "editorial_confidence": 76,
            },
            {
                "key": "yahoo_finance",
                "name": "Yahoo Finance",
                "url": "https://finance.yahoo.com/news/rssindex",
                "focus": "markets",
                "editorial_confidence": 80,
            },
        ],
    )


def downgrade() -> None:
    source_catalog = sa.table(
        "source_catalog",
        sa.column("key", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("url", sa.Text()),
        sa.column("focus", _FOCUS_ENUM),
        sa.column("editorial_confidence", sa.Integer()),
    )
    op.execute(
        source_catalog.delete().where(
            source_catalog.c.key.in_(("cointelegraph", "yahoo_finance"))
        )
    )
    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "coindesk")
        .values(url="https://www.coindesk.com")
    )
    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "decrypt")
        .values(url="https://decrypt.co")
    )
    op.bulk_insert(
        source_catalog,
        [
            {"key": "ft", "name": "Financial Times", "url": "https://www.ft.com",
             "focus": "markets", "editorial_confidence": 90},
            {"key": "wsj", "name": "Wall Street Journal", "url": "https://www.wsj.com",
             "focus": "markets", "editorial_confidence": 88},
            {"key": "bloomberg", "name": "Bloomberg", "url": "https://www.bloomberg.com",
             "focus": "markets", "editorial_confidence": 92},
            {"key": "reuters", "name": "Reuters", "url": "https://www.reuters.com",
             "focus": "markets", "editorial_confidence": 90},
        ],
    )
