/**
 * TeamActivityScreen — the Team section's full activity history. Same
 * seeded-cache harness convention as TeamHomeScreen.test.tsx: no chat/
 * messaging surface exists here (explicitly out of scope this wave), only a
 * read-only real event log.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as ReactReduxNS from 'react-redux';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as StoreNS from '../../../store';
import type * as TeamActivityScreenNS from './TeamActivityScreen';
import type { MeResponse, WorkspaceActivityListResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ME = { workspace: { id: 'ws-1', role: 'owner' }, account: { id: 'acc-owner' } } as unknown as MeResponse;

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

function renderScreen(me: MeResponse, activity: WorkspaceActivityListResponse) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { TeamActivityScreen } = req('./TeamActivityScreen') as typeof TeamActivityScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  qc.setQueryData(['me'], me);
  qc.setQueryData(['workspace', 'activity'], activity);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(TeamActivityScreen),
        }),
      }),
    );
  });

  const rendered = () => JSON.stringify(tree.toJSON());
  return { tree, act, rendered };
}

test('renders real invited/joined/removed events with their real, describable copy', () => {
  const activity: WorkspaceActivityListResponse = {
    events: [
      {
        id: 'evt-3',
        event: 'member_removed',
        actorAccountId: 'acc-owner',
        subjectAccountId: 'acc-editor',
        subjectEmail: null,
        role: 'editor',
        previousRole: null,
        createdAt: '2026-07-26T14:00:00Z',
      },
      {
        id: 'evt-2',
        event: 'member_joined',
        actorAccountId: 'acc-editor',
        subjectAccountId: 'acc-editor',
        subjectEmail: null,
        role: 'editor',
        previousRole: null,
        createdAt: '2026-07-26T13:00:00Z',
      },
      {
        id: 'evt-1',
        event: 'member_invited',
        actorAccountId: 'acc-owner',
        subjectAccountId: null,
        subjectEmail: 'friend@oryx.test',
        role: 'editor',
        previousRole: null,
        createdAt: '2026-07-26T12:00:00Z',
      },
    ],
  };
  const { tree, act, rendered } = renderScreen(ME, activity);

  assert.ok(rendered().includes('joined as Editor'));
  assert.ok(rendered().includes('friend@oryx.test was invited as Editor'));
  assert.ok(rendered().includes('was removed'));
  assert.ok(rendered().includes('3 EVENTS'));

  act(() => tree.unmount());
});

test('no events: renders the honest empty state, not a fake placeholder row', () => {
  const { tree, act, rendered } = renderScreen(ME, { events: [] });
  assert.ok(rendered().includes('No team activity yet'));
  act(() => tree.unmount());
});
