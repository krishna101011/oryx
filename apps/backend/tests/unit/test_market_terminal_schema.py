"""Phase 9 Wave A — schema-shape checks, no DB required. Mirrors
test_training_schema.py's convention of asserting real ORM metadata
(columns, primary keys, unique constraints) rather than convention alone.

Symbol is platform-wide (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md
§2/§3) — no workspace_id, same reasoning as Course (Phase 8). Watchlist is
scoped to account_id only, deliberately NOT workspace_id — §3's real
decision, mirroring AlertPreference's account_id-only precedent for a
personal-to-the-user setting.
"""
from __future__ import annotations

from decimal import Decimal

from oryx.core.models import PriceBar, Symbol, Watchlist, WatchlistItem


def test_symbol_has_no_workspace_id_column() -> None:
    assert "workspace_id" not in Symbol.__table__.columns.keys()


def test_symbol_ticker_and_exchange_are_jointly_unique() -> None:
    unique_col_sets = {
        frozenset(c.name for c in constraint.columns)
        for constraint in Symbol.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert frozenset({"ticker", "exchange"}) in unique_col_sets


def test_price_bar_primary_key_is_symbol_timeframe_and_bar_time() -> None:
    pk_cols = {c.name for c in PriceBar.__table__.primary_key.columns}
    assert pk_cols == {"symbol_id", "timeframe", "bar_time"}


def test_price_bar_has_no_synthetic_id_column() -> None:
    """The composite (symbol_id, timeframe, bar_time) key is the real dedup
    key for a re-fetchable cache row (§3) — there should be no separate
    `id` column implying a different identity."""
    assert "id" not in PriceBar.__table__.columns.keys()


def test_price_bar_ohlcv_columns_accept_real_decimal_precision() -> None:
    """Not a placeholder float — real Numeric precision wide enough for
    both large equity prices and fractional crypto volumes (§3)."""
    for col_name in ("open", "high", "low", "close", "volume"):
        col = PriceBar.__table__.columns[col_name]
        assert col.type.python_type is Decimal
        assert not col.nullable


def test_watchlist_is_scoped_to_account_not_workspace() -> None:
    """§3's real decision: personal per-account, mirroring
    AlertPreference's account_id-only precedent — never shared across a
    workspace's teammates."""
    columns = Watchlist.__table__.columns.keys()
    assert "account_id" in columns
    assert "workspace_id" not in columns


def test_watchlist_name_defaults_to_default() -> None:
    col = Watchlist.__table__.columns["name"]
    assert col.server_default is not None
    assert col.server_default.arg == "Default"


def test_watchlist_account_and_name_are_jointly_unique() -> None:
    unique_col_sets = {
        frozenset(c.name for c in constraint.columns)
        for constraint in Watchlist.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert frozenset({"account_id", "name"}) in unique_col_sets


def test_watchlist_item_primary_key_is_watchlist_and_symbol() -> None:
    pk_cols = {c.name for c in WatchlistItem.__table__.primary_key.columns}
    assert pk_cols == {"watchlist_id", "symbol_id"}
