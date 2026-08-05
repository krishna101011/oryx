/**
 * Phase 9 Wave B — a small, hardcoded placeholder OHLC dataset used ONLY to
 * prove the rendering pipeline (web direct render + native WebView bridge)
 * draws real candles end to end. No vendor is wired up yet
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §3) — this is not real
 * market data and must never be presented as such once a real screen
 * (Wave D) replaces it with MarketDataProvider output.
 *
 * `time` is a UNIX timestamp in seconds (lightweight-charts' `Time` type),
 * one bar per day, matching PriceBar's `bar_time` semantics (core/models.py).
 */
import type { MarketChartBar } from './marketChartBridge';

const DAY_SECONDS = 86400;
const START_TIME = 1735689600; // 2025-01-01T00:00:00Z, arbitrary fixed anchor

export const PLACEHOLDER_CANDLES: MarketChartBar[] = [
  { open: 100.0, high: 102.5, low: 99.1, close: 101.8 },
  { open: 101.8, high: 103.2, low: 100.9, close: 102.6 },
  { open: 102.6, high: 102.9, low: 100.1, close: 100.7 },
  { open: 100.7, high: 101.4, low: 98.3, close: 98.9 },
  { open: 98.9, high: 100.2, low: 98.0, close: 99.8 },
  { open: 99.8, high: 101.9, low: 99.5, close: 101.6 },
  { open: 101.6, high: 104.1, low: 101.3, close: 103.7 },
  { open: 103.7, high: 105.0, low: 102.8, close: 104.4 },
  { open: 104.4, high: 104.6, low: 101.9, close: 102.3 },
  { open: 102.3, high: 103.0, low: 100.5, close: 100.9 },
  { open: 100.9, high: 102.2, low: 100.4, close: 101.9 },
  { open: 101.9, high: 103.8, low: 101.7, close: 103.4 },
  { open: 103.4, high: 103.9, low: 102.0, close: 102.5 },
  { open: 102.5, high: 102.8, low: 99.6, close: 100.1 },
  { open: 100.1, high: 101.5, low: 99.9, close: 101.2 },
].map((bar, index) => ({ ...bar, time: START_TIME + index * DAY_SECONDS }));
