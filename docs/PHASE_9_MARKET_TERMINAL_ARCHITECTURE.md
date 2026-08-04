# ORYX — Phase 9 Market Terminal Architecture

**Scope:** Phase 9 — the roadmap's Markets/Charting territory. Two distinct
screens confirmed real from `docs/design-reference/screens/`: Markets
Terminal (macro overview) and Technical Analysis (the deep charting
workspace). A third mockup, Opportunities, exists in the same directory but
has no charting-specific content and is explicitly deferred to its own
future reconsideration — not part of this buildout.
**Status:** DRAFT — Rev 1. Real decisions below; not yet built, not yet
recon-verified against running code (there is no Phase 9 code to verify
against — this is greenfield).
**Depends on:** the Protocol + factory provider pattern already proven
three times (`core/ai_provider.py`, `core/payment_provider.py`,
`core/video_provider.py`); the existing `Platform.OS === 'web'` branching
pattern (`packages/design-system/src/components/Card.tsx`,
`apps/mobile/src/components/WebFrame.tsx`); Phase 4's `intelligence_objects`
claims (Technical Analysis's "Linked claims" panel ties verified claims to
a symbol — real join confirmed in Wave D, not assumed here).
**Blocked on (greenfield, confirmed absent):** `Symbol` / price-bar-OHLCV
cache / `Watchlist` / `WatchlistItem` schema (grepped — no such classes
anywhere in `apps/backend/src/oryx`; latest migration is
`0036_phase8_training_foundation.py`); `react-native-webview` (not a
dependency of `apps/mobile` today, confirmed via `package.json` — no
existing WebView pattern anywhere in this codebase, web or native); any
real market-data vendor selection (deferred by the project owner until the
platform is further built out); order-book live data and portfolio
overlays (see §5).

---

## Revision Note

Rev 1. No prior revision exists. This is the first real scoping pass for
Phase 9, grounded in two confirmed design-reference mockups
(`terminal.jsx`, `technical.jsx`, 180 lines each) and a direct check of
what already exists in the codebase to build on (the three prior provider
implementations, the web-branching pattern, the total absence of any RN
WebView usage).

## 1. Real IA, Confirmed From Design-Reference

**Markets Terminal** (`terminal.jsx`) — the macro overview:
- Sector-weighted heatmap (six sectors: AI/Semis, Mega tech, Crypto,
  Energy, Financials, Defensive; 1H/24H/7D toggle; per-symbol tile sized
  and colored by change magnitude).
- Economic calendar (time, region, event, importance chip, forecast,
  prior).
- A screener table (symbol, name, last, change%, 24h volume, market cap,
  an "ORYX score" meter, a signal chip, an inline sparkline).
- Earnings calendar (symbol, company, BMO/AMC timing, EPS estimate,
  revenue estimate) alongside a monthly event-calendar grid.

**Technical Analysis** (`technical.jsx`) — the deep charting workspace, a
three-pane layout (44px drawing-tool rail | chart canvas | 280px right
rail):
- Left rail: drawing tools (cursor, trendline, fib, position, note, box)
  plus layers/settings.
- Center: symbol header with live price and change, timeframe tabs
  (1m/5m/15m/1H/4H/1D/1W), layout tabs (Single/Split/Quad/+News), an
  indicator bar (EMA 9/21/50, VWAP, Bollinger Bands — each with its own
  plot color), a candlestick chart canvas, an RSI(14) subchart, and a
  bottom status bar (drawn-object count, alert count, snapshot age, open
  position P&L).
- Right rail: Watchlist table, Order Book (L2 bid/ask depth with spread),
  and **Linked claims** — verified claims tied to the current symbol, each
  with a confidence meter. This is the direct tie-in to Phase 4's
  `intelligence_objects`/claims; the real join key is confirmed in Wave D,
  not assumed here.

**Opportunities** (`opportunities.jsx`, 103 lines) exists as a mockup but
has no charting-specific content. Explicitly deferred to its own future
reconsideration — out of scope for this phase.

## 2. Charting Technology

**TradingView Lightweight Charts** (free, open-source, canvas-based).

Confirmed real integration path: **web** renders it directly via the
existing `Platform.OS === 'web'` branching pattern already used in
`Card.tsx`/`WebFrame.tsx`. **Native has no existing WebView pattern
anywhere in this codebase** — `react-native-webview` is not installed.
This is real, new, additional scope, not a small addition: a fresh
dependency plus a real message-passing bridge (crosshair position, visible
range, drawing-tool state) between the WebView-hosted chart and the React
Native app. Scoped as its own deliberate wave (Wave B, §4) — not bundled
into a screen wave.

## 3. MarketDataProvider — The Fourth Instance of the Proven Pattern

Mirrors `core/ai_provider.py` / `core/payment_provider.py` /
`core/video_provider.py` exactly: a narrow `Protocol`, vendor errors
collapsed onto a shared error-kind taxonomy, a factory
(`get_market_data_provider(settings)`) that picks the concrete
implementation so callers never branch on vendor. Unlike
`video_provider.py` — which has one real vendor chosen (Cloudflare
Stream) and is just missing live credentials — Phase 9 has **no vendor
chosen at all**, deferred by the project owner until the platform is
further built out. So the factory's only real implementation for Rev 1 is
an honest `NotConfiguredMarketDataProvider` that raises
`MarketDataProviderError(kind=PERMANENT, message="no market data vendor
configured")` on every call — the same honest-absence shape as the other
three providers' missing-credential guards, just one level earlier (no
vendor at all, not merely no credentials for a chosen one).

Real schema needed regardless of vendor (Wave A, greenfield — confirmed
absent; latest migration is `0036_phase8_training_foundation.py`):
- **Symbol** — id, ticker, display name, asset class (equity/crypto/etc.),
  exchange, currency.
- **Price-bar / OHLCV cache table** — symbol_id, timeframe, open, high,
  low, close, volume, bar timestamp. A cache, not a source of truth;
  populated by whatever vendor is eventually chosen.
- **Watchlist** — id, owning account/workspace (decide the exact scope in
  Wave A against the mockup's per-account watchlist).
- **WatchlistItem** — watchlist_id, symbol_id, order.

Every screen renders fully and honestly with this schema empty: real UI,
real layout (heatmap grid, screener table, chart canvas, watchlist rows,
order-book depth), and a genuine "market data not connected yet" state
wherever live prices would render. Never fabricated numbers — the same
discipline already established for the uncredentialed
`CloudflareStreamProvider` and the dev-default `LogOnlyPushProvider`.

## 4. Wave Sequencing

This phase is too large for one wave.

- **Wave A** — Schema (`Symbol`, price-bar/OHLCV cache, `Watchlist`,
  `WatchlistItem`) + `MarketDataProvider` abstraction (Protocol + factory +
  `NotConfiguredMarketDataProvider`). Backend only, no screens.
- **Wave B** — TradingView Lightweight Charts integration, web direct
  render + native WebView bridge (the new `react-native-webview`
  dependency, the message-passing bridge for crosshair/visible-range/
  drawing-tool state). No real screen content yet — this wave proves the
  rendering pipeline works end to end against empty/placeholder data.
- **Wave C** — Markets Terminal screen (heatmap, economic calendar,
  screener, earnings calendar) — mostly Card/HairlineRowList patterns,
  lower technical risk since it embeds no chart.
- **Wave D** — Technical Analysis screen (the full charting workspace:
  timeframes, layout tabs, indicator bar, drawing-tool rail, candlestick
  chart via Wave B's bridge, RSI subchart, watchlist, order book, linked-
  claims panel) — depends on Waves A–C being real and working; this is
  where the Phase 4 claims tie-in (§1) gets its real, confirmed join.

## 5. Explicitly Out of Scope for Rev 1

Opportunities (separate future reconsideration — no charting-specific
mockup exists for it). Any real market-data vendor selection or
integration (deferred by the project owner). Order-book live data
(depends on a vendor decision not yet made — the mockup's order book is
randomly generated demo data, not a real feed). Portfolio overlays (no
reference mockup exists for this — flagged as unconfirmed scope, not
assumed).
