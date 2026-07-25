"""Source catalog: repoint the_block to its real, confirmed RSS feed.

Revision ID: 0028_catalog_the_block_feed
Revises: 0027_catalog_investing_feeds
Create Date: 2026-07-25

the_block was the one entry migration 0026 deliberately left untouched:
recon at the time found no confirmed working feed URL, so it stayed on its
homepage URL (https://www.theblock.co) rather than being guessed at.

Follow-up recon (this migration) found the real feed: probing common feed
paths on theblock.co, https://www.theblock.co/rss.xml returns HTTP 200 with
a genuine RSS 2.0 document (channel title "The Block", live dated articles,
standard content/dc/atom/media namespaces) — confirmed live-checked
immediately before this migration was written, same standard as 0026/0027.
(https://www.theblock.co/api/rss also returns HTTP 200 but its body is
`{"error":"Route not found"}` — a JSON error page, not a feed; rejected.)

This migration only updates `url` on the existing the_block row. The key,
name, focus, and editorial_confidence are untouched, and no other catalog
entry is touched.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0028_catalog_the_block_feed"
down_revision = "0027_catalog_investing_feeds"
branch_labels = None
depends_on = None

_OLD_URL = "https://www.theblock.co"
_NEW_URL = "https://www.theblock.co/rss.xml"


def upgrade() -> None:
    source_catalog = sa.table(
        "source_catalog", sa.column("key", sa.Text()), sa.column("url", sa.Text())
    )
    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "the_block")
        .values(url=_NEW_URL)
    )


def downgrade() -> None:
    source_catalog = sa.table(
        "source_catalog", sa.column("key", sa.Text()), sa.column("url", sa.Text())
    )
    op.execute(
        source_catalog.update()
        .where(source_catalog.c.key == "the_block")
        .values(url=_OLD_URL)
    )
