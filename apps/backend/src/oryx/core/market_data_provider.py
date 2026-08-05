"""Pluggable market-data provider abstraction. Mirrors core/ai_provider.py,
core/payment_provider.py, and core/video_provider.py's exact shape: one
narrow Protocol, vendor errors collapsed onto a shared taxonomy before
crossing the boundary, a factory that picks the concrete implementation so
callers never branch on vendor.

Real decision (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §3): UNLIKE
the other three providers, no vendor is chosen yet — deferred by the
project owner until the platform is further built out. So this module has
no real vendor implementation at all (no CloudflareStreamProvider-style
class), only NotConfiguredMarketDataProvider, which conforms to the
Protocol and raises MarketDataProviderError(kind=PERMANENT) on every real
method, unconditionally. This is one level earlier than the other three
providers' "chosen vendor, missing live credentials" guard — here there is
no chosen vendor to be missing credentials FOR yet.
get_market_data_provider() always returns this today; wiring a real
vendor branch into the factory is a future wave's job, not this one's.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class MarketDataProviderErrorKind(str, Enum):
    TRANSIENT = "transient"        # 5xx, network blip, timeout
    RATE_LIMITED = "rate_limited"  # 429
    AUTH = "auth"                  # API key/token rejected
    PERMANENT = "permanent"        # missing config, bad request, unknown symbol
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketDataProviderError(Exception):
    kind: MarketDataProviderErrorKind
    message: str
    provider: str
    retry_after_seconds: int | None = None

    def __str__(self) -> str:  # pragma: no cover — trivial
        return f"{self.provider}/{self.kind.value}: {self.message}"


@dataclass(frozen=True)
class SymbolMatch:
    """Returned by search_symbols. Fields mirror Symbol's real columns
    (core/models.py) — a real vendor's search result, not yet persisted;
    the caller decides whether to create a Symbol row from it."""

    ticker: str
    display_name: str
    exchange: str
    asset_class: str


@dataclass(frozen=True)
class Quote:
    """Returned by get_quote. A live snapshot, never cached — price_bars
    (core/models.py) is the OHLCV cache; a Quote is the "right now" value
    a vendor's real-time endpoint would return."""

    ticker: str
    price: float
    change_abs: float
    change_pct: float
    as_of: datetime


@dataclass(frozen=True)
class Bar:
    """Returned by get_bars. Maps 1:1 onto PriceBar's real columns
    (core/models.py) — the caller writes these into the price_bars cache
    table; this dataclass itself is never persisted directly."""

    bar_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@runtime_checkable
class MarketDataProvider(Protocol):
    name: str

    async def search_symbols(self, *, query: str) -> list[SymbolMatch]: ...

    async def get_quote(self, *, ticker: str) -> Quote: ...

    async def get_bars(
        self, *, ticker: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Bar]: ...


class NotConfiguredMarketDataProvider:
    """The only real implementation this wave — no vendor is chosen
    (§3), so every method raises PERMANENT unconditionally, pre-flight,
    exactly like CloudflareStreamProvider's missing-credential guard in
    video_provider.py — just one level earlier: there is no vendor to be
    missing credentials for yet."""

    name = "not_configured"

    def _unconfigured(self) -> MarketDataProviderError:
        return MarketDataProviderError(
            kind=MarketDataProviderErrorKind.PERMANENT,
            message="no market data vendor is configured yet",
            provider=self.name,
        )

    async def search_symbols(self, *, query: str) -> list[SymbolMatch]:
        raise self._unconfigured()

    async def get_quote(self, *, ticker: str) -> Quote:
        raise self._unconfigured()

    async def get_bars(
        self, *, ticker: str, timeframe: str, start: datetime, end: datetime
    ) -> list[Bar]:
        raise self._unconfigured()


def get_market_data_provider(settings: object) -> MarketDataProvider:
    """Factory. No real vendor exists today (§3) — always returns the
    honest not-configured implementation. `settings` is accepted (and
    currently unused) purely for signature symmetry with
    get_ai_provider/get_payment_provider/get_video_provider — a future
    wave adds real vendor branching here once one is chosen, the same
    single-implementation shape get_video_provider had before Wave A."""
    return NotConfiguredMarketDataProvider()
