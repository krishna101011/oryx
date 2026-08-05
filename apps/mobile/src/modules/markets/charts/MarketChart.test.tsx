/**
 * Phase 9 Wave B — proves <MarketChart/> picks the right platform-specific
 * implementation at render time (the "shared component shape" requirement),
 * not just that it compiles. Same shim-harness pattern as
 * research/rowNavigation.test.tsx: only the platform layer (react-native,
 * react-native-webview) is shimmed to inert hosts; MarketChart/MarketChartWeb/
 * MarketChartNative themselves run for real.
 *
 * Platform.OS is mutated directly on the shimmed 'react-native' module
 * (read live at MarketChart's render time, not captured at import time —
 * same reason Card.tsx/WebFrame.tsx's own `Platform.OS === 'web'` checks
 * work) to exercise both branches from one test file without a second
 * shim variant.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as RNNS from 'react-native';
import type * as MarketChartNS from './MarketChart';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

function renderMarketChart() {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { MarketChart } = req('./MarketChart') as typeof MarketChartNS;

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(React.createElement(MarketChart, { bars: [] }));
  });
  return tree;
}

// Restricted to host (string-type) instances: the shimmed View/WebView are
// forwardRef wrappers around a host element and both spread `...props`, so
// an unfiltered findAll would double-count each match (wrapper + host).
function findByTestId(tree: ReactTestRenderer, testID: string) {
  return tree.root.findAll(
    (node) => typeof node.type === 'string' && node.props.testID === testID,
  );
}

function findByType(tree: ReactTestRenderer, type: string) {
  return tree.root.findAll((node) => (node.type as unknown) === type);
}

test('on web (Platform.OS default), MarketChart renders MarketChartWeb — no WebView in the tree', () => {
  const RN = req('react-native') as typeof RNNS;
  (RN.Platform as { OS: string }).OS = 'web';

  const tree = renderMarketChart();
  assert.equal(findByTestId(tree, 'market-chart-web').length, 1);
  assert.equal(findByType(tree, 'WebView').length, 0);

  tree.unmount();
});

test('on native (Platform.OS !== web), MarketChart renders MarketChartNative — a real WebView, not a DOM chart', () => {
  const RN = req('react-native') as typeof RNNS;
  (RN.Platform as { OS: string }).OS = 'ios';

  const tree = renderMarketChart();
  assert.equal(findByTestId(tree, 'market-chart-native').length, 1);
  assert.equal(findByType(tree, 'WebView').length, 1);
  assert.equal(findByTestId(tree, 'market-chart-web').length, 0);

  tree.unmount();
  (RN.Platform as { OS: string }).OS = 'web'; // restore — Platform is a shared shim module instance
});

test('android also takes the native branch (OS check is "=== web", not an ios/android allowlist)', () => {
  const RN = req('react-native') as typeof RNNS;
  (RN.Platform as { OS: string }).OS = 'android';

  const tree = renderMarketChart();
  assert.equal(findByTestId(tree, 'market-chart-native').length, 1);

  tree.unmount();
  (RN.Platform as { OS: string }).OS = 'web';
});
