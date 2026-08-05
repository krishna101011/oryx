/**
 * Test-only lightweight-charts shim (MarketChartWeb, Phase 9 Wave B). See
 * ./react-native.js. `lightweight-charts` needs a real DOM/canvas to do
 * anything and ships ESM-only (no CJS `require` export condition) — both
 * make it unloadable as the real package under `tsx --test`'s plain Node
 * CJS require. Never actually exercised: MarketChartWeb's `if (!el) return;`
 * guard means `createChart` is never called under react-test-renderer
 * (host refs resolve to null there), so these stubs only need to exist,
 * not behave like the real library.
 */
const fakeSeries = {
  setData() {},
};
const fakeChart = {
  addSeries: () => fakeSeries,
  timeScale: () => ({
    fitContent() {},
    subscribeVisibleTimeRangeChange() {},
  }),
  subscribeCrosshairMove() {},
  remove() {},
};

module.exports = {
  __esModule: true,
  createChart: () => fakeChart,
  CandlestickSeries: 'CandlestickSeries',
};
