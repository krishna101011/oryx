/**
 * Analytics blank-render fix (2026-07-25) — Overview/Research/Publishing
 * tabs each did `if (!data) return null`, so an in-flight query rendered
 * literally nothing: no skeleton, no spinner, no text, the whole tab body
 * blank. Each now does `if (isLoading || !data) return <Skeleton .../>`, an
 * interim generic-Skeleton fix (the real shaped skeleton comes later). Real
 * AnalyticsHomeScreen, real Redux store, real react-query, real FeatureGate
 * (needs ff_analytics on).
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as ReactReduxNS from 'react-redux';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as DesignSystemNS from '@oryx/design-system';
import type * as StoreNS from '../../../store';
import type * as ClientNS from '../../../lib/api/client';
import type * as AnalyticsScreenNS from './AnalyticsHomeScreen';
import type { Analytics, MeResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ME = { workspace: { id: 'ws-1' }, flags: { ff_analytics: true } } as unknown as MeResponse;

const EMPTY_ROLLUPS: Analytics.AnalyticsRollupsResponse = {
  series: {},
  from: '2026-07-19',
  to: '2026-07-25',
};

const REAL_ROLLUPS: Analytics.AnalyticsRollupsResponse = {
  series: { intake_items_received: [{ date: '2026-07-25', value: 5 }] },
  from: '2026-07-19',
  to: '2026-07-25',
};

const EMPTY_PUBLISHING: Analytics.AnalyticsPublishingResponse = {
  success: { published: 0, failed: 0, successRate: null },
  timeToPublish: { averageSeconds: null, medianSeconds: null, sampleSize: 0 },
};

const REAL_PUBLISHING: Analytics.AnalyticsPublishingResponse = {
  success: { published: 10, failed: 1, successRate: 0.9 },
  timeToPublish: { averageSeconds: 3600, medianSeconds: 3000, sampleSize: 10 },
};

function setAuthenticated(store: { dispatch: (action: unknown) => void }) {
  const { authActions } = req('../../../store/slices/auth') as {
    authActions: { tokensSet: (p: unknown) => { type: string; payload: unknown } };
  };
  store.dispatch(
    authActions.tokensSet({
      accessToken: 'a',
      refreshToken: 'r',
      accountId: 'acc-1',
      sessionId: 'sess-1',
      accessTokenExpiresAt: '2099-01-01T00:00:00Z',
    }),
  );
}

function pressByLabel(tree: ReactTestRenderer, act: (cb: () => void) => void, label: string) {
  const matches = tree.root.findAll(
    (node) =>
      (node.type as unknown) === 'Pressable' &&
      node.props.accessibilityLabel === label &&
      typeof node.props.onPress === 'function',
  );
  assert.equal(matches.length, 1, `exactly one pressable labeled "${label}"`);
  act(() => {
    matches[0]!.props.onPress();
  });
}

/** Seeds rollups + publishing normally (staleTime: Infinity — no fetch). */
function renderAnalytics(
  rollups: Analytics.AnalyticsRollupsResponse,
  publishing: Analytics.AnalyticsPublishingResponse,
) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { AnalyticsHomeScreen } = req('./AnalyticsHomeScreen') as typeof AnalyticsScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['me'], ME);
  qc.setQueryData(['analytics', 'rollups'], rollups);
  qc.setQueryData(['analytics', 'publishing'], publishing);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(AnalyticsHomeScreen),
        ),
      ),
    );
  });

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

/** Deliberately leaves both analytics queries unseeded, with a fetch that
 * never resolves, so both stay `isLoading: true` for the assertion. */
function renderAnalyticsLoading() {
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (() =>
    new Promise<Response>(() => {})) as unknown as typeof fetch;

  const { configureApiClient } = req('../../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { AnalyticsHomeScreen } = req('./AnalyticsHomeScreen') as typeof AnalyticsScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['me'], ME);
  // ['analytics', 'rollups'] and ['analytics', 'publishing'] deliberately unseeded.

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(AnalyticsHomeScreen),
        ),
      ),
    );
  });

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()), restore };
}

test('Overview tab while loading shows 3 shaped SkeletonTiles (label+value+trend+sparkline), never a blank body', () => {
  const { tree, act, rendered, restore } = renderAnalyticsLoading();
  const { SkeletonTile } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(
    tree.root.findAllByType(SkeletonTile as never).length,
    3,
    'one shaped SkeletonTile per real KPI card (Items ingested / Claims verified / Drafts published)',
  );
  assert.ok(!rendered().includes('Still gathering data'));

  act(() => tree.unmount());
  restore();
});

test('Research tab while loading shows the real funnel-card shell with 4 shaped funnel rows, never a blank body', () => {
  const { tree, act, rendered, restore } = renderAnalyticsLoading();
  const { Card, Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Research');

  assert.equal(tree.root.findAllByType(Card as never).length, 1, 'the real funnel Card shell renders');
  // Bespoke SkeletonFunnelRow isn't exported (single consumer) — verify its
  // real composition instead: 2 title/caption bars + 4 rows x (2 head bars +
  // 1 exact-height track bar) = 14 Skeleton primitives.
  assert.equal(tree.root.findAllByType(Skeleton as never).length, 14);
  assert.ok(!rendered().includes('No research activity yet'));

  act(() => tree.unmount());
  restore();
});

test('Publishing tab while loading shows 2 shaped SkeletonTiles (label+value+detail line), never a blank body', () => {
  const { tree, act, rendered, restore } = renderAnalyticsLoading();
  const { SkeletonTile } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Publishing');

  assert.equal(
    tree.root.findAllByType(SkeletonTile as never).length,
    2,
    'one shaped SkeletonTile per real card (Delivery success / Time to publish)',
  );
  assert.ok(!rendered().includes('Nothing published yet'));

  act(() => tree.unmount());
  restore();
});

test('Overview tab with real data shows real KPI tiles, no Skeleton, no empty copy', () => {
  const { tree, act, rendered } = renderAnalytics(REAL_ROLLUPS, REAL_PUBLISHING);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Items ingested'));
  assert.ok(!rendered().includes('Still gathering data'));

  act(() => tree.unmount());
});

test('Overview tab genuinely empty (loaded, zero rollup rows) shows the real "still gathering" copy, no Skeleton', () => {
  const { tree, act, rendered } = renderAnalytics(EMPTY_ROLLUPS, EMPTY_PUBLISHING);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Still gathering data'));

  act(() => tree.unmount());
});

test('Research tab genuinely empty shows the real "no research activity" copy, no Skeleton', () => {
  const { tree, act, rendered } = renderAnalytics(EMPTY_ROLLUPS, EMPTY_PUBLISHING);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Research');

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('No research activity yet'));

  act(() => tree.unmount());
});

test('Publishing tab genuinely empty shows the real "nothing published yet" copy, no Skeleton', () => {
  const { tree, act, rendered } = renderAnalytics(EMPTY_ROLLUPS, EMPTY_PUBLISHING);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Publishing');

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Nothing published yet'));

  act(() => tree.unmount());
});

test('Publishing tab with real data shows real delivery stats, no Skeleton, no empty copy', () => {
  const { tree, act, rendered } = renderAnalytics(REAL_ROLLUPS, REAL_PUBLISHING);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Publishing');

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('90%'));
  assert.ok(!rendered().includes('Nothing published yet'));

  act(() => tree.unmount());
});
