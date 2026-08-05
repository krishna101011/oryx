"""Phase 9 Wave A — Market Terminal schema foundation
(docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §3).

Creates symbols, price_bars, watchlists, watchlist_items. `symbols` is
platform-wide — no workspace_id, same reasoning as Phase 8's `courses`
(a shared catalog, not a per-workspace resource). `price_bars` is
explicitly a CACHE (no vendor is wired up yet — §3's
NotConfiguredMarketDataProvider is the real state this wave), keyed by
(symbol_id, timeframe, bar_time) so a re-fetch naturally dedups instead
of needing a synthetic id. `watchlists` is scoped to account_id only, no
workspace_id — mirrors the existing `alert_preferences` precedent for a
setting that's personal to the user even though the app runs inside a
workspace context.

Revision ID: 0037_phase9_market_foundation
Revises: 0036_phase8_training_foundation
Create Date: 2026-08-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0037_phase9_market_foundation"
down_revision = "0036_phase8_training_foundation"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column(
            "asset_class",
            sa.Enum("equity", "crypto", name="symbol_asset_class"),
            nullable=False,
        ),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("ticker", "exchange", name="uq_symbols_ticker_exchange"),
    )

    op.create_table(
        "price_bars",
        sa.Column(
            "symbol_id",
            _UUID,
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "timeframe",
            sa.Enum("1m", "5m", "15m", "1H", "4H", "1D", "1W", name="bar_timeframe"),
            primary_key=True,
        ),
        sa.Column("bar_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "watchlists",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column(
            "account_id",
            _UUID,
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "name", sa.Text(), nullable=False, server_default="Default"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("account_id", "name", name="uq_watchlists_account_name"),
    )
    op.create_index("idx_watchlists_account", "watchlists", ["account_id"])

    op.create_table(
        "watchlist_items",
        sa.Column(
            "watchlist_id",
            _UUID,
            sa.ForeignKey("watchlists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "symbol_id",
            _UUID,
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_index("idx_watchlists_account", table_name="watchlists")
    op.drop_table("watchlists")
    op.drop_table("price_bars")
    op.drop_table("symbols")
