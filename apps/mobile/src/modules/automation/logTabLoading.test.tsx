/**
 * Automation Hub Log tab loading-vs-empty conflation fix (2026-07-25).
 *
 * Before this fix, `LogTab` derived its rows from `entries ?? []` with no
 * separate loading signal, so an in-flight /automation-log fetch and a
 * genuinely empty log both rendered the SAME "Nothing in the log yet"
 * EmptyState — indistinguishable to the user. `isLoading` now gates a
 * generic Skeleton first. Same real-render harness as expandOnPress.test.tsx
 * (real AutomationHubScreen, real Redux store, real react-query).
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
import type * as StoreNS from '../../store';
import type * as ClientNS from '../../lib/api/client';
import type * as HubScreenNS from './screens/AutomationHubScreen';
import type { AlertPreference, Automation, MeResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

/** Just enough of /auth/me for FeatureGate (flags) + useMe's workspace effect. */
const ME = {
  workspace: { id: 'ws-1' },
  flags: { ff_automation: true },
} as unknown as MeResponse;

const PREFS: AlertPreference[] = (
  ['security', 'system', 'verification', 'publishing'] as const
).flatMap((type) =>
  (['in_app', 'push', 'email'] as const).map(
    (channel) =>
      ({ type, channel, frequency: 'instant', quietHours: null }) as AlertPreference,
  ),
);

const LOG: Automation.AutomationLogResponse = {
  entries: [
    {
      id: 'f0000000-0000-0000-0000-000000000001',
      kind: 'dispatch',
      action: 'notification_created',
      eventType: 'content.published',
      category: null,
      frequency: null,
      windowStart: null,
      windowEnd: null,
      activityInboxId: null,
      channel: 'in_app',
      detail: null,
      createdAt: '2026-07-15T09:00:00Z',
    },
  ],
};

const EMPTY_LOG: Automation.AutomationLogResponse = { entries: [] };

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

/** Seeds `['automation','log']` normally (staleTime: Infinity — no fetch). */
function renderHubWithLog(log: Automation.AutomationLogResponse) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { AutomationHubScreen } = req(
    './screens/AutomationHubScreen',
  ) as typeof HubScreenNS;

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['me'], ME);
  qc.setQueryData(['alerts', 'preferences'], PREFS);
  qc.setQueryData(['automation', 'log'], log);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(AutomationHubScreen),
        ),
      ),
    );
  });

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

/** Deliberately leaves `['automation','log']` (and, when `seedPrefs` is
 * false, `['alerts','preferences']` too) unseeded, with a fetch that never
 * resolves, so the relevant query stays `isLoading: true` for the
 * assertion. */
function renderHubLoading(seedPrefs = true) {
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (() =>
    new Promise<Response>(() => {})) as unknown as typeof fetch;

  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { AutomationHubScreen } = req(
    './screens/AutomationHubScreen',
  ) as typeof HubScreenNS;

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['me'], ME);
  if (seedPrefs) qc.setQueryData(['alerts', 'preferences'], PREFS);
  // ['automation', 'log'] (and ['alerts', 'preferences'] when seedPrefs is
  // false) deliberately unseeded.

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        Provider,
        { store, children: undefined } as ReactReduxNS.ProviderProps,
        React.createElement(
          QueryClientProvider,
          { client: qc },
          React.createElement(AutomationHubScreen),
        ),
      ),
    );
  });

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()), restore };
}

test('Log tab while loading shows 3 shaped SkeletonRows (stacked time/date + title + outcome chip), never the "Nothing in the log yet" empty copy', () => {
  const { tree, act, rendered, restore } = renderHubLoading();
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Log');

  assert.equal(
    tree.root.findAllByType(SkeletonRow as never).length,
    3,
    'one shaped SkeletonRow per real LogRow anatomy',
  );
  assert.ok(
    !rendered().includes('Nothing in the log yet'),
    'the empty-state copy must not appear while still loading',
  );

  act(() => tree.unmount());
  restore();
});

test('KPI row while loading (prefs or log in flight) shows 3 shaped SkeletonTiles, never the real "—" fallback', () => {
  const { tree, act, restore } = renderHubLoading();
  const { SkeletonTile } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(
    tree.root.findAllByType(SkeletonTile as never).length,
    3,
    'one shaped SkeletonTile per real KPI (Active rules / Decisions·24h / Failures·24h)',
  );

  act(() => tree.unmount());
  restore();
});

test('Rules tab while loading shows 3 shaped, flanked SkeletonRows (category chip + cadence chip), not the real "—" cadence fallback', () => {
  const { tree, act, restore } = renderHubLoading(false);
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  // Rules is the default tab — no press needed.
  assert.equal(
    tree.root.findAllByType(SkeletonRow as never).length,
    3,
    'one shaped SkeletonRow per real RuleRow anatomy',
  );

  act(() => tree.unmount());
  restore();
});

test('Log tab with a real, non-empty log shows the real rows, no Skeleton, no empty copy', () => {
  const { tree, act, rendered } = renderHubWithLog(LOG);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Log');

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Notification delivered'));
  assert.ok(!rendered().includes('Nothing in the log yet'));

  act(() => tree.unmount());
});

test('Log tab genuinely empty (loaded, zero entries) shows the real empty-state copy, no Skeleton', () => {
  const { tree, act, rendered } = renderHubWithLog(EMPTY_LOG);
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  pressByLabel(tree, act, 'Log');

  assert.equal(tree.root.findAllByType(Skeleton as never).length, 0);
  assert.ok(rendered().includes('Nothing in the log yet'));

  act(() => tree.unmount());
});
