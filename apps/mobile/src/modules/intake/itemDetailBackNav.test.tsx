/**
 * IntakeItemDetail back-navigation (2026-07-25 wave).
 *
 * ActivityHomeScreen opens this screen with a cross-tab navigate
 * ('Settings', {screen: 'IntakeItemDetail'}), which PUSHES it onto whatever
 * the Settings stack already holds (usually just SettingsHome) — so the
 * default back button popped to SettingsHome, not back to Activity. The fix
 * (ItemDetailScreen.tsx) tags Activity's navigate with `origin: 'activity'`
 * and intercepts every dismissal path via `beforeRemove`, redirecting to the
 * Activity tab instead — but ONLY for that origin, so Dashboard's Today row
 * and web search (same screen, no `origin`) keep their unchanged behavior.
 *
 * Real ItemDetailScreen, real react-query cache (no network) — only the
 * navigation object is faked, exactly like rowNavigation.test.tsx's
 * established pattern, extended here to also capture addListener/dispatch/
 * getParent since that's the surface this fix actually exercises.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactNavigationNS from '@react-navigation/native';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ItemDetailScreenNS from './screens/ItemDetailScreen';
import type { IntakeItemDetail } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ITEM_ID = 'a3a5f3a0-0000-4000-8000-000000000001';

const ITEM: IntakeItemDetail = {
  id: ITEM_ID,
  subject: 'Fed holds rates steady',
  bodyText: 'The FOMC voted to hold the target range unchanged.',
  senderLabel: 'Reuters Wire',
  senderDomain: 'reuters.com',
  links: [],
  sourceName: 'Reuters',
  providerName: 'rss',
  receivedAt: '2026-07-25T10:00:00Z',
};

/** A fake navigation prop exposing exactly the surface ItemDetailScreen
 * calls (addListener/getParent/dispatch), recording every call so the test
 * can assert on them, and letting the test manually fire the captured
 * beforeRemove listener the way a real back press would. */
function makeFakeNavigation() {
  const listeners: Record<string, ((e: unknown) => void) | undefined> = {};
  const parentCalls: { name: string; params: unknown }[] = [];
  const dispatchCalls: unknown[] = [];

  const parent = {
    navigate: (name: string, params?: unknown) => {
      parentCalls.push({ name, params });
    },
  };

  const navigation = {
    addListener: (event: string, cb: (e: unknown) => void) => {
      listeners[event] = cb;
      return () => {
        listeners[event] = undefined;
      };
    },
    getParent: () => parent,
    dispatch: (action: unknown) => {
      dispatchCalls.push(action);
    },
  };

  return { navigation, listeners, parentCalls, dispatchCalls };
}

function renderItemDetail(params: { itemId: string; origin?: 'activity' }) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext, NavigationRouteContext } = req(
    '@react-navigation/native',
  ) as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { ItemDetailScreen } = req('./screens/ItemDetailScreen') as typeof ItemDetailScreenNS;

  const fake = makeFakeNavigation();

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['intake', 'item', params.itemId], ITEM);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          NavigationContext.Provider,
          { value: fake.navigation as never },
          React.createElement(
            NavigationRouteContext.Provider,
            { value: { key: 'IntakeItemDetail-test', name: 'IntakeItemDetail', params } as never },
            React.createElement(ItemDetailScreen),
          ),
        ),
      ),
    );
  });

  return { tree, act, ...fake };
}

test('Activity entry point (origin: "activity"): back is intercepted and redirects to the Activity tab', () => {
  const { tree, act, listeners, parentCalls, dispatchCalls } = renderItemDetail({
    itemId: ITEM_ID,
    origin: 'activity',
  });

  const beforeRemove = listeners['beforeRemove'];
  assert.equal(typeof beforeRemove, 'function', 'a beforeRemove listener is registered');

  let prevented = false;
  const FAKE_ACTION = { type: 'GO_BACK' };
  act(() => {
    beforeRemove!({ preventDefault: () => (prevented = true), data: { action: FAKE_ACTION } });
  });

  assert.equal(prevented, true, 'the default pop (which would land on SettingsHome) is cancelled');
  assert.deepEqual(
    parentCalls,
    [{ name: 'Activity', params: undefined }],
    'the parent tab navigator is told to switch to Activity',
  );
  assert.deepEqual(
    dispatchCalls,
    [FAKE_ACTION],
    'the original action is replayed so the Settings stack still cleans up IntakeItemDetail',
  );

  act(() => tree.unmount());
});

test('regression — no origin (Dashboard Today row / web search): back is NOT intercepted, default pop is untouched', () => {
  const { tree, act, listeners, parentCalls, dispatchCalls } = renderItemDetail({
    itemId: ITEM_ID,
  });

  assert.equal(
    listeners['beforeRemove'],
    undefined,
    'no beforeRemove listener registered — the screen keeps its normal Settings-stack back behavior',
  );
  assert.deepEqual(parentCalls, []);
  assert.deepEqual(dispatchCalls, []);

  act(() => tree.unmount());
});
