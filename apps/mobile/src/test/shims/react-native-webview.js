/**
 * Test-only react-native-webview shim (MarketChartNative, Phase 9 Wave B).
 * See ./react-native.js. Renders as an inert host element forwarding props;
 * `postMessage`/`injectJavaScript`/`reload` are no-ops on the ref, matching
 * the real WebView's imperative API shape without any real native module.
 */
const React = require('react');

const WebView = React.forwardRef((props, ref) => {
  React.useImperativeHandle(ref, () => ({
    postMessage() {},
    injectJavaScript() {},
    reload() {},
    goBack() {},
    goForward() {},
    stopLoading() {},
    requestFocus() {},
  }));
  return React.createElement('WebView', props);
});
WebView.displayName = 'WebView';

module.exports = { __esModule: true, WebView, default: WebView };
