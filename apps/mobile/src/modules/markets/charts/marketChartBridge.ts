/**
 * Phase 9 Wave B — the MarketChart bridge message contract.
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B)
 *
 * Pure logic, no RN/DOM import — this is the SAME contract MarketChartWeb
 * uses internally (calling the callback props directly, no serialization)
 * and MarketChartNative uses across the WebView's real postMessage bridge
 * (JSON-encoded both directions), so a screen consuming <MarketChart/>
 * (Wave D) sees identical shapes regardless of platform.
 *
 * native -> WebView: load_data (the only message native ever sends this
 * wave — placeholder bars only, no live vendor).
 * WebView -> native: crosshair_move, visible_range_change (state a real
 * screen would want to mirror into its own UI, e.g. a price readout).
 */

export interface MarketChartBar {
  time: number; // UNIX seconds
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LoadDataMessage {
  type: 'load_data';
  bars: MarketChartBar[];
}

export interface CrosshairMoveMessage {
  type: 'crosshair_move';
  time: number | null;
  price: number | null;
}

export interface VisibleRangeChangeMessage {
  type: 'visible_range_change';
  from: number;
  to: number;
}

export type NativeToWebMessage = LoadDataMessage;
export type WebToNativeMessage = CrosshairMoveMessage | VisibleRangeChangeMessage;

export function encodeNativeToWebMessage(message: NativeToWebMessage): string {
  return JSON.stringify(message);
}

function isMarketChartBar(value: unknown): value is MarketChartBar {
  if (typeof value !== 'object' || value === null) return false;
  const bar = value as Record<string, unknown>;
  return (
    typeof bar.time === 'number' &&
    typeof bar.open === 'number' &&
    typeof bar.high === 'number' &&
    typeof bar.low === 'number' &&
    typeof bar.close === 'number'
  );
}

/** Decodes a raw WebView `onMessage` payload. Returns null for anything that
 * isn't valid JSON or doesn't match a known message shape — the caller
 * (MarketChartNative) drops unrecognized payloads rather than crashing on a
 * malformed or future-version message from the WebView side. */
export function decodeNativeToWebMessage(raw: string): NativeToWebMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null) return null;
  const message = parsed as Record<string, unknown>;
  if (message.type === 'load_data' && Array.isArray(message.bars) && message.bars.every(isMarketChartBar)) {
    return { type: 'load_data', bars: message.bars };
  }
  return null;
}

export function decodeWebToNativeMessage(raw: string): WebToNativeMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null) return null;
  const message = parsed as Record<string, unknown>;

  if (message.type === 'crosshair_move') {
    const time = message.time;
    const price = message.price;
    if ((typeof time === 'number' || time === null) && (typeof price === 'number' || price === null)) {
      return { type: 'crosshair_move', time: time ?? null, price: price ?? null };
    }
    return null;
  }

  if (message.type === 'visible_range_change') {
    if (typeof message.from === 'number' && typeof message.to === 'number') {
      return { type: 'visible_range_change', from: message.from, to: message.to };
    }
    return null;
  }

  return null;
}
