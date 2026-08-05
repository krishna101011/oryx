/**
 * Phase 9 Wave B — native WebView bridge.
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B)
 *
 * Loads marketChartHtml.ts's real HTML (lightweight-charts + the init
 * script) into a WebView with no runtime network dependency, then proves
 * the bridge is bidirectional:
 *   native -> WebView: on `onLoadEnd`, `webViewRef.postMessage(...)` sends a
 *     real `load_data` message (encodeNativeToWebMessage) carrying `bars`.
 *   WebView -> native: `onMessage` decodes each real payload
 *     (decodeWebToNativeMessage) and forwards crosshair/visible-range
 *     events to the caller via props — malformed/unrecognized payloads are
 *     dropped, never crash the app.
 */
import React, { useCallback, useRef } from 'react';
import { StyleSheet } from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';
import {
  decodeWebToNativeMessage,
  encodeNativeToWebMessage,
  type CrosshairMoveMessage,
  type MarketChartBar,
  type VisibleRangeChangeMessage,
} from './marketChartBridge';
import { buildMarketChartHtml } from './marketChartHtml';

export interface MarketChartNativeProps {
  bars: MarketChartBar[];
  onCrosshairMove?: (message: CrosshairMoveMessage) => void;
  onVisibleRangeChange?: (message: VisibleRangeChangeMessage) => void;
  testID?: string;
}

export const MarketChartNative: React.FC<MarketChartNativeProps> = ({
  bars,
  onCrosshairMove,
  onVisibleRangeChange,
  testID,
}) => {
  const webViewRef = useRef<WebView>(null);

  const handleLoadEnd = useCallback(() => {
    webViewRef.current?.postMessage(encodeNativeToWebMessage({ type: 'load_data', bars }));
  }, [bars]);

  const handleMessage = useCallback(
    (event: WebViewMessageEvent) => {
      const message = decodeWebToNativeMessage(event.nativeEvent.data);
      if (!message) return;
      if (message.type === 'crosshair_move') onCrosshairMove?.(message);
      if (message.type === 'visible_range_change') onVisibleRangeChange?.(message);
    },
    [onCrosshairMove, onVisibleRangeChange],
  );

  return (
    <WebView
      ref={webViewRef}
      testID={testID ?? 'market-chart-native'}
      originWhitelist={['*']}
      source={{ html: buildMarketChartHtml() }}
      onLoadEnd={handleLoadEnd}
      onMessage={handleMessage}
      style={styles.webview}
    />
  );
};

const styles = StyleSheet.create({
  webview: { flex: 1, minHeight: 320, backgroundColor: 'transparent' },
});
