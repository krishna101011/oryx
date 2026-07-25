/**
 * ActivityHomeScreen -> IntakeItemDetail navigation (2026-07-25 wave).
 *
 * Complements itemDetailBackNav.test.tsx: that file proves ItemDetailScreen
 * redirects back to Activity when it receives `origin: 'activity'`; THIS
 * file proves Activity's row press is actually the one real caller that
 * sets it (a real render, real press, real navigate call), so the two
 * pieces of the fix stay provably wired together rather than each assuming
 * the other holds up its end.
 *
 * Real ActivityHomeScreen + real react-query cache (seeded, no network) +
 * fake fetch for the mark-read mutation side effect — same convention as
 * catalogActivationWiring.test.tsx.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactNavigationNS from '@react-navigation/native';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ClientNS from '../../lib/api/client';
import type * as ActivityScreenNS from './screens/ActivityHomeScreen';
import type * as PressableNS from '@oryx/design-system';
import type { ActivityInboxResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ITEM_ID = 'a3a5f3a0-0000-4000-8000-000000000001';

const INBOX: ActivityInboxResponse = {
  unreadCount: 1,
  items: [
    {
      id: 'row-1',
      type: 'system',
      title: 'New item ingested',
      body: 'Reuters: Fed holds rates steady',
      data: { intakeItemId: ITEM_ID, workspaceId: 'ws-1' },
      readAt: null,
      createdAt: '2026-07-25T10:00:00Z',
    },
    {
      id: 'row-2',
      type: 'security',
      title: 'New sign-in',
      body: 'A new device signed in',
      data: { sessionId: 's-1' },
      readAt: '2026-07-25T09:00:00Z',
      createdAt: '2026-07-25T09:00:00Z',
    },
  ],
};

function renderActivityHome() {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext } = req(
    '@react-navigation/native',
  ) as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  const { Pressable } = req('@oryx/design-system') as typeof PressableNS;
  const { ActivityHomeScreen } = req('./screens/ActivityHomeScreen') as typeof ActivityScreenNS;

  const navigateCalls: { name: string; params: unknown }[] = [];
  const fakeNavigation = { navigate: (name: string, params?: unknown) => {
    navigateCalls.push({ name, params });
  } };

  const fetchCalls: { method: string; path: string }[] = [];
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (async (input: unknown, init?: RequestInit) => {
    const path = String(input).replace(/^https?:\/\/[^/]+\/v1/, '');
    fetchCalls.push({ method: (init?.method ?? 'GET').toUpperCase(), path });
    return new Response(JSON.stringify({ data: {} }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
  }) as typeof fetch;

  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['activity', 'inbox'], INBOX);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          NavigationContext.Provider,
          { value: fakeNavigation as never },
          React.createElement(ActivityHomeScreen),
        ),
      ),
    );
  });

  const press = (index: number) => {
    const pressables = tree.root.findAllByType(Pressable as never);
    act(() => {
      (pressables[index]!.props as { onPress: () => void }).onPress();
    });
  };

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, navigateCalls, fetchCalls, press, restore };
}

test('pressing an intake-backed row navigates to Settings/IntakeItemDetail tagged origin: "activity"', () => {
  const { tree, navigateCalls, press, restore } = renderActivityHome();

  press(0); // "New item ingested" row — carries intakeItemId

  assert.deepEqual(navigateCalls, [
    {
      name: 'Settings',
      params: { screen: 'IntakeItemDetail', params: { itemId: ITEM_ID, origin: 'activity' } },
    },
  ]);

  tree.unmount();
  restore();
});

test('pressing a row with no intake item behind it never navigates (mark-read only)', () => {
  const { tree, navigateCalls, press, restore } = renderActivityHome();

  press(1); // "New sign-in" row — no intakeItemId in its payload

  assert.deepEqual(navigateCalls, []);

  tree.unmount();
  restore();
});
