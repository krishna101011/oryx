"""core/market_data_provider.py — Phase 9 Wave A. Mirrors
test_video_provider.py's unconfigured-state coverage, one level earlier:
no vendor is chosen at all (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md
§3), so NotConfiguredMarketDataProvider must raise a clean, typed
MarketDataProviderError(PERMANENT) on every real method, unconditionally
— never attempt a live call, never crash raw.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from oryx.core.market_data_provider import (
    MarketDataProvider,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    NotConfiguredMarketDataProvider,
    get_market_data_provider,
)


def _provider() -> NotConfiguredMarketDataProvider:
    return NotConfiguredMarketDataProvider()


@pytest.mark.asyncio
async def test_search_symbols_rejects_unconfigured_vendor() -> None:
    provider = _provider()
    with pytest.raises(MarketDataProviderError) as exc:
        await provider.search_symbols(query="BTC")
    assert exc.value.kind == MarketDataProviderErrorKind.PERMANENT
    assert "no market data vendor" in exc.value.message


@pytest.mark.asyncio
async def test_get_quote_rejects_unconfigured_vendor() -> None:
    provider = _provider()
    with pytest.raises(MarketDataProviderError) as exc:
        await provider.get_quote(ticker="BTC")
    assert exc.value.kind == MarketDataProviderErrorKind.PERMANENT


@pytest.mark.asyncio
async def test_get_bars_rejects_unconfigured_vendor() -> None:
    provider = _provider()
    now = datetime.now(UTC)
    with pytest.raises(MarketDataProviderError) as exc:
        await provider.get_bars(ticker="BTC", timeframe="1H", start=now, end=now)
    assert exc.value.kind == MarketDataProviderErrorKind.PERMANENT


def test_factory_always_returns_not_configured_provider_today() -> None:
    """No vendor exists yet (§3) — the factory has nothing to branch on,
    unlike get_video_provider's real-vendor-but-maybe-uncredentialed
    shape. Any settings object, real or empty, gets the same result."""
    provider = get_market_data_provider(SimpleNamespace())
    assert isinstance(provider, NotConfiguredMarketDataProvider)
    assert provider.name == "not_configured"


def test_not_configured_provider_satisfies_the_protocol() -> None:
    """Structural proof the honest stub really is a MarketDataProvider,
    not just something shaped like one by convention."""
    assert isinstance(_provider(), MarketDataProvider)
