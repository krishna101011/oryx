/**
 * Phase 9 Wave B — marketChartHtml.ts's inline script is untranspiled plain
 * JS text (it runs inside the WebView's own JS context, never through
 * tsc/tsx), so it cannot literally import marketChartBridge.ts's types. This
 * test is the mechanical drift guard the module's own header comment
 * promises: it asserts the generated HTML string's message shapes stay
 * byte-identical to the real bridge contract's literal `type` values and
 * field names, so a future edit to one side can't silently diverge from the
 * other.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildMarketChartHtml } from './marketChartHtml';

test('the generated HTML embeds the real lightweight-charts bundle, not a placeholder', () => {
  const html = buildMarketChartHtml();
  assert.match(html, /window\.LightweightCharts\s*=/);
  assert.match(html, /Lightweight Charts™ v5\.2\.0/);
});

test('the generated HTML creates a chart and a candlestick series', () => {
  const html = buildMarketChartHtml();
  assert.match(html, /LightweightCharts\.createChart\(/);
  assert.match(html, /LightweightCharts\.CandlestickSeries/);
});

test('the WebView-to-native direction emits crosshair_move with the real bridge field names', () => {
  const html = buildMarketChartHtml();
  assert.match(html, /type:\s*'crosshair_move'/);
  assert.match(html, /post\(\{\s*type:\s*'crosshair_move',\s*time:\s*param\.time \|\| null,\s*price:\s*price\s*\}\)/);
});

test('the WebView-to-native direction emits visible_range_change with the real bridge field names', () => {
  const html = buildMarketChartHtml();
  assert.match(html, /type:\s*'visible_range_change',\s*from:\s*range\.from,\s*to:\s*range\.to/);
});

test('the native-to-WebView direction listens for load_data on BOTH document and window (the real Android/iOS split)', () => {
  const html = buildMarketChartHtml();
  assert.match(html, /message\.type === 'load_data'/);
  assert.match(html, /document\.addEventListener\('message', handleMessage\)/);
  assert.match(html, /window\.addEventListener\('message', handleMessage\)/);
});

test('every message type literal used by the HTML matches marketChartBridge.ts', () => {
  const html = buildMarketChartHtml();
  // Covers both shapes the inline script uses: object-literal construction
  // (`type: 'x'`, the two outbound messages) and comparison (`=== 'x'`, the
  // one inbound message this wave handles).
  const htmlTypes = new Set(
    Array.from(html.matchAll(/(?:type:|message\.type ===)\s*'([a-z_]+)'/g)).map((m) => m[1]),
  );
  assert.deepEqual(htmlTypes, new Set(['crosshair_move', 'visible_range_change', 'load_data']));
});
