/**
 * Command Center "Today" card loading-vs-empty conflation fix (2026-07-25).
 *
 * `dashboard/stats.ts`'s `todayPanelState` has always defined a real
 * `{ kind: 'loading' }` state, but DashboardScreen only ever branched on
 * `'empty'` and `'list'` — while `useRecentIntakeItems()` was in flight, the
 * Today card rendered a header with a genuinely empty body (neither branch
 * matched). A `'loading'` branch now renders a generic Skeleton. Real
 * DashboardScreen, real Redux store (useMe needs `status: 'authenticated'`
 * to even enable its query), real react-query.
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
import type * as DashboardScreenNS from './DashboardScreen';
import type { IntakeStatusSummary, MeResponse, RecentIntakeItem } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

/** Just enough of /auth/me for the hero summary + KPI tiles. */
const ME = {
  workspace: { id: 'ws-1' },
  verification: { pendingReviewCount: 2, openConflictCount: 0, verifiedCount: 7 },
  content: { draftCount: 3, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
} as unknown as MeResponse;

const STATUS: IntakeStatusSummary = {
  total: 4,
  byHealth: { healthy: 4, degraded: 0, auth_required: 0, disabled: 0 },
};

const ITEMS: RecentIntakeItem[] = [
  {
    id: 'item-1',
    subject: 'Fed holds rates steady',
    sourceName: 'Reuters',
    providerName: 'rss',
    receivedAt: '2026-07-25T10:00:00Z',
  } as RecentIntakeItem,
];

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

/** Seeds all three queries (staleTime: Infinity — no real fetch). */
function renderDashboard(recentItems: RecentIntakeItem[] | undefined) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { DashboardScreen } = req('./DashboardScreen') as typeof DashboardScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['me'], ME);
  qc.setQueryData(['intake', 'status'], STATUS);
  if (recentItems !== undefined) {
    qc.setQueryData(['intake', 'recent-items', 10], recentItems);
  }

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(DashboardScreen),
        ),
      ),
    );
  });

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

/** Deliberately leaves the recent-items query (and, when `seedKpiData` is
 * false, `me`/`intake status` too) unseeded, with a fetch that never
 * resolves, so the relevant query stays `isLoading: true` for the
 * assertion. */
function renderDashboardLoading(seedKpiData = true) {
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
  const { DashboardScreen } = req('./DashboardScreen') as typeof DashboardScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (seedKpiData) {
    qc.setQueryData(['me'], ME);
    qc.setQueryData(['intake', 'status'], STATUS);
  }
  // ['intake', 'recent-items', 10] (and ['me']/['intake','status'] when
  // seedKpiData is false) deliberately unseeded.

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(DashboardScreen),
        ),
      ),
    );
  });

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()), restore };
}

test('Today card while loading shows 3 shaped SkeletonRows (tag chip + 2-line headline + meta), never a blank card body', () => {
  const { tree, act, rendered, restore } = renderDashboardLoading();
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(
    tree.root.findAllByType(SkeletonRow as never).length,
    3,
    'one shaped SkeletonRow per real Today row anatomy',
  );
  assert.ok(
    !rendered().includes('Nothing to surface yet'),
    'the empty-state copy must not appear while still loading',
  );

  act(() => tree.unmount());
  restore();
});

test('KPI row while loading (intake status or /me in flight) shows 3 shaped SkeletonTiles, never the real "—" fallback', () => {
  const { tree, act, restore } = renderDashboardLoading(false);
  const { SkeletonTile } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(
    tree.root.findAllByType(SkeletonTile as never).length,
    3,
    'one shaped SkeletonTile per real KPI (SOURCES / VERIFIED / DRAFTS)',
  );

  act(() => tree.unmount());
  restore();
});

test('Today card with real recent items shows the real rows, no Skeleton, no empty copy', () => {
  const { tree, act, rendered } = renderDashboard(ITEMS);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Fed holds rates steady'));
  assert.ok(!rendered().includes('Nothing to surface yet'));

  act(() => tree.unmount());
});

test('Today card genuinely empty (loaded, zero items) shows the real empty copy, no Skeleton', () => {
  const { tree, act, rendered } = renderDashboard([]);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Nothing to surface yet'));

  act(() => tree.unmount());
});
