/**
 * Phase 9 Wave B — the bridge message contract, both directions. Pure logic,
 * no shims needed (marketChartBridge.ts imports nothing from react-native).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  decodeNativeToWebMessage,
  decodeWebToNativeMessage,
  encodeNativeToWebMessage,
  type MarketChartBar,
} from './marketChartBridge';

const BAR: MarketChartBar = { time: 1735689600, open: 100, high: 102.5, low: 99.1, close: 101.8 };

test('encodeNativeToWebMessage produces JSON the WebView-side handler can round-trip via decodeNativeToWebMessage', () => {
  const raw = encodeNativeToWebMessage({ type: 'load_data', bars: [BAR] });
  const decoded = decodeNativeToWebMessage(raw);
  assert.deepEqual(decoded, { type: 'load_data', bars: [BAR] });
});

test('decodeNativeToWebMessage rejects a load_data payload with a malformed bar (missing field)', () => {
  const raw = JSON.stringify({ type: 'load_data', bars: [{ time: 1, open: 1, high: 1, low: 1 }] });
  assert.equal(decodeNativeToWebMessage(raw), null);
});

test('decodeNativeToWebMessage rejects invalid JSON without throwing', () => {
  assert.equal(decodeNativeToWebMessage('{not json'), null);
});

test('decodeWebToNativeMessage accepts a real crosshair_move payload (both fields present)', () => {
  const raw = JSON.stringify({ type: 'crosshair_move', time: 1735689600, price: 101.8 });
  assert.deepEqual(decodeWebToNativeMessage(raw), {
    type: 'crosshair_move',
    time: 1735689600,
    price: 101.8,
  });
});

test('decodeWebToNativeMessage accepts crosshair_move with null time/price (cursor off the chart)', () => {
  const raw = JSON.stringify({ type: 'crosshair_move', time: null, price: null });
  assert.deepEqual(decodeWebToNativeMessage(raw), { type: 'crosshair_move', time: null, price: null });
});

test('decodeWebToNativeMessage accepts a real visible_range_change payload', () => {
  const raw = JSON.stringify({ type: 'visible_range_change', from: 1735689600, to: 1736294400 });
  assert.deepEqual(decodeWebToNativeMessage(raw), {
    type: 'visible_range_change',
    from: 1735689600,
    to: 1736294400,
  });
});

test('decodeWebToNativeMessage rejects visible_range_change missing a required field', () => {
  const raw = JSON.stringify({ type: 'visible_range_change', from: 1735689600 });
  assert.equal(decodeWebToNativeMessage(raw), null);
});

test('decodeWebToNativeMessage rejects an unrecognized message type rather than guessing', () => {
  const raw = JSON.stringify({ type: 'something_else', foo: 'bar' });
  assert.equal(decodeWebToNativeMessage(raw), null);
});

test('decodeWebToNativeMessage rejects invalid JSON without throwing', () => {
  assert.equal(decodeWebToNativeMessage('not even json'), null);
});
