/**
 * Phase 9 Wave B — web direct render.
 * (docs/PHASE_9_MARKET_TERMINAL_ARCHITECTURE.md §2/§4 Wave B)
 *
 * Renders lightweight-charts directly into the real DOM node behind an RN
 * Web `View`, same ref-cast pattern Card.tsx already uses
 * (`viewRef.current as unknown as HTMLElement`). Under react-test-renderer
 * (no real DOM — the mobile test harness) that ref resolves to `null`, so
 * the effect's `if (!el) return;` guard — the same guard Card.tsx relies on
 * — makes this safe to mount in a render test without a real browser.
 *
 * `lightweight-charts` is a STATIC top-level import, not dynamic. A dynamic
 * `import()` was tried first (to route around the package's lack of a CJS
 * `require` export condition, which broke a static import under the
 * Node/tsx test harness) but broke for real: live Expo web threw
 * `Error: Requiring unknown module "2804"` from Metro's async-chunk loader
 * (`asyncRequireImpl`/`importAll`) — this Expo SDK 51 / Metro 0.80.12 setup
 * does not reliably serve lazily-split chunks in dev. Metro's own resolver
 * (unlike Node's strict ESM `exports`-map resolution) ignores the `exports`
 * field entirely at this Metro version and just follows the package's
 * legacy `main` field, so a STATIC import resolves fine in the real bundle.
 * The test-harness gap this reintroduces is closed the same way this repo
 * already closes it for every other native-only package: a shim
 * (src/test/shims/lightweight-charts.js) — never exercised for real here
 * since the `if (!el) return;` guard above means `createChart` is never
 * actually called under react-test-renderer.
 *
 * No bridge serialization needed here: crosshair/visible-range callbacks
 * call the shared MarketChartBridge prop callbacks directly, in-process —
 * the "bridge" only needs real postMessage plumbing on native
 * (MarketChartNative.tsx).
 */
import React, { useEffect, useRef } from 'react';
import { View } from 'react-native';
import { useTheme } from '@oryx/design-system';
import { CandlestickSeries, createChart, type IChartApi, type UTCTimestamp } from 'lightweight-charts';
import type {
  CrosshairMoveMessage,
  MarketChartBar,
  VisibleRangeChangeMessage,
} from './marketChartBridge';

export interface MarketChartWebProps {
  bars: MarketChartBar[];
  onCrosshairMove?: (message: CrosshairMoveMessage) => void;
  onVisibleRangeChange?: (message: VisibleRangeChangeMessage) => void;
  testID?: string;
}

export const MarketChartWeb: React.FC<MarketChartWebProps> = ({
  bars,
  onCrosshairMove,
  onVisibleRangeChange,
  testID,
}) => {
  const t = useTheme();
  const containerRef = useRef<View>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = containerRef.current as unknown as HTMLElement | null;
    if (!el) return;

    const chart = createChart(el, {
      layout: { background: { color: t.colors.bg.primary }, textColor: t.colors.text.secondary },
      grid: {
        vertLines: { color: t.colors.border.default },
        horzLines: { color: t.colors.border.default },
      },
      width: el.clientWidth,
      height: el.clientHeight || 320,
    });
    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: t.colors.semantic.positiveText,
      downColor: t.colors.semantic.danger,
      borderVisible: false,
      wickUpColor: t.colors.semantic.positiveText,
      wickDownColor: t.colors.semantic.danger,
    });
    // `time` is a plain UNIX-seconds number in our own bridge contract
    // (marketChartBridge.ts); lightweight-charts wants its branded
    // UTCTimestamp — same numeric value, cast at the one point the two
    // contracts meet.
    series.setData(bars.map((bar) => ({ ...bar, time: bar.time as UTCTimestamp })));
    chart.timeScale().fitContent();

    chart.subscribeCrosshairMove((param) => {
      if (!onCrosshairMove) return;
      const point = param.seriesData?.get(series) as { close?: number; value?: number } | undefined;
      onCrosshairMove({
        type: 'crosshair_move',
        time: (param.time as number | undefined) ?? null,
        price: point?.close ?? point?.value ?? null,
      });
    });

    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (!range || !onVisibleRangeChange) return;
      onVisibleRangeChange({
        type: 'visible_range_change',
        from: range.from as number,
        to: range.to as number,
      });
    });

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // Placeholder-data proof only (Wave B) — the chart is created once per
    // mount, not re-synced on every `bars` change. Real data updates are a
    // Wave D concern once a screen owns this component's lifecycle.
  }, []);

  return <View ref={containerRef} testID={testID ?? 'market-chart-web'} style={{ flex: 1, minHeight: 320 }} />;
};
