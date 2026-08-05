/**
 * Phase 9 Wave B — the HTML page loaded into MarketChartNative's WebView.
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B)
 *
 * Embeds the real lightweight-charts standalone bundle (no runtime network
 * dependency — see gen-market-chart-bundle.ts), creates a chart + candlestick
 * series, and wires the real postMessage bridge:
 *   native -> WebView: `webViewRef.postMessage(...)` delivers a `load_data`
 *     message; this page listens on BOTH `document` and `window` `message`
 *     events (react-native-webview's own documented Android/iOS split —
 *     Android delivers via `document`, iOS via `window`).
 *   WebView -> native: `window.ReactNativeWebView.postMessage(...)` on every
 *     real crosshair move / visible-range change, picked up by
 *     MarketChartNative's `onMessage` prop.
 *
 * This inline script is untranspiled plain JS text injected into a WebView's
 * own JS context — it cannot literally import marketChartBridge.ts. Its
 * message shapes are hand-kept identical to that module's
 * LoadDataMessage/CrosshairMoveMessage/VisibleRangeChangeMessage on purpose;
 * marketChartHtml.test.ts asserts the exact field names/literal `type`
 * values appear in the generated string so drift is caught mechanically.
 */
import { LIGHTWEIGHT_CHARTS_STANDALONE_JS } from './lightweightChartsBundle.generated';

const CHART_INIT_SCRIPT = `
(function () {
  var chart = LightweightCharts.createChart(document.getElementById('chart'), {
    layout: { background: { color: '#05070A' }, textColor: '#A8B0BF' },
    grid: { vertLines: { color: '#1A2330' }, horzLines: { color: '#1A2330' } },
    width: window.innerWidth,
    height: window.innerHeight,
  });
  var series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: '#30A3E9',
    downColor: '#F87171',
    borderVisible: false,
    wickUpColor: '#30A3E9',
    wickDownColor: '#F87171',
  });

  function post(message) {
    if (window.ReactNativeWebView) {
      window.ReactNativeWebView.postMessage(JSON.stringify(message));
    }
  }

  chart.subscribeCrosshairMove(function (param) {
    var price = null;
    if (series && param.seriesData && param.seriesData.get(series)) {
      var d = param.seriesData.get(series);
      price = d.close != null ? d.close : (d.value != null ? d.value : null);
    }
    post({ type: 'crosshair_move', time: param.time || null, price: price });
  });

  chart.timeScale().subscribeVisibleTimeRangeChange(function (range) {
    if (!range) return;
    post({ type: 'visible_range_change', from: range.from, to: range.to });
  });

  function handleMessage(event) {
    var message;
    try {
      message = JSON.parse(event.data);
    } catch (e) {
      return;
    }
    if (message && message.type === 'load_data' && Array.isArray(message.bars)) {
      series.setData(message.bars);
      chart.timeScale().fitContent();
    }
  }
  document.addEventListener('message', handleMessage);
  window.addEventListener('message', handleMessage);

  window.addEventListener('resize', function () {
    chart.applyOptions({ width: window.innerWidth, height: window.innerHeight });
  });
})();
`;

export function buildMarketChartHtml(): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <style>html, body, #chart { margin: 0; padding: 0; width: 100%; height: 100%; background: #05070A; }</style>
</head>
<body>
  <div id="chart"></div>
  <script>${LIGHTWEIGHT_CHARTS_STANDALONE_JS}</script>
  <script>${CHART_INIT_SCRIPT}</script>
</body>
</html>`;
}
