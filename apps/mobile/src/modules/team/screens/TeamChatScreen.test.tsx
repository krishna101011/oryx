/**
 * TeamChatScreen — real Card/HairlineRowList anatomy + react-query polling,
 * same harness convention as TeamHomeScreen.test.tsx (fake fetch backend,
 * not a seeded cache, since this screen's whole point is live send/edit/
 * delete/poll round trips). Covers the three behaviors this wave was asked
 * to prove: own-vs-other row styling, edit/delete restricted to the
 * sender's own messages, and the poll loop passing a real narrowing cursor
 * on the second request instead of re-fetching from scratch.
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
import type * as ClientNS from '../../../lib/api/client';
import type * as TeamChatScreenNS from './TeamChatScreen';
import type { ChatMessage, MeResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ME_OWNER = { workspace: { id: 'ws-1', role: 'owner' }, account: { id: 'acc-owner' } } as unknown as MeResponse;

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

function makeFakeChatBackend(seed: ChatMessage[], currentAccountId: string) {
  const messages = [...seed];
  const calls: { method: string; path: string; body: unknown }[] = [];
  let sendCounter = 0;

  const json = (data: unknown): Response =>
    new Response(
      JSON.stringify({ data, meta: { requestId: 'r', serverTime: '2026-07-27T00:00:00Z' } }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  const page = (data: ChatMessage[], nextCursor: string | null): Response =>
    new Response(
      JSON.stringify({
        data,
        meta: {
          requestId: 'r',
          serverTime: '2026-07-27T00:00:00Z',
          pagination: { nextCursor, prevCursor: null },
        },
      }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  const errorJson = (code: string, message: string, status: number): Response =>
    new Response(
      JSON.stringify({ error: { code, message, requestId: 'test-request-id' } }),
      { status, headers: { 'content-type': 'application/json' } },
    );

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const url = new URL(String(input));
    const path = url.pathname.replace(/^\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: path + url.search, body });

    if (method === 'GET' && path === '/workspaces/messages') {
      const since = url.searchParams.get('since');
      const slice = since
        ? messages.slice(messages.findIndex((m) => m.id === since) + 1)
        : messages;
      const nextCursor =
        slice.length > 0 ? slice[slice.length - 1]!.id : (since ?? messages.at(-1)?.id ?? null);
      return page(slice, nextCursor);
    }
    if (method === 'POST' && path === '/workspaces/messages') {
      sendCounter += 1;
      const created: ChatMessage = {
        id: `sent-${sendCounter}`,
        workspaceId: 'ws-1',
        senderAccountId: currentAccountId,
        body: (body as { body: string }).body,
        createdAt: `2026-07-27T00:1${sendCounter}:00Z`,
        editedAt: null,
        deletedAt: null,
      };
      messages.push(created);
      return json(created);
    }
    const editMatch = /^\/workspaces\/messages\/(.+)$/.exec(path);
    if (method === 'PATCH' && editMatch) {
      const target = messages.find((m) => m.id === editMatch[1]);
      if (!target || target.senderAccountId !== currentAccountId) {
        return errorJson('PERMISSION_DENIED', 'not_sender', 403);
      }
      target.body = (body as { body: string }).body;
      target.editedAt = '2026-07-27T00:20:00Z';
      return json(target);
    }
    if (method === 'DELETE' && editMatch) {
      const target = messages.find((m) => m.id === editMatch[1]);
      if (!target || target.senderAccountId !== currentAccountId) {
        return errorJson('PERMISSION_DENIED', 'not_sender', 403);
      }
      target.body = null;
      target.deletedAt = '2026-07-27T00:21:00Z';
      return json({ deleted: true });
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls };
}

function renderScreen(seed: ChatMessage[], me: MeResponse = ME_OWNER) {
  const backend = makeFakeChatBackend(seed, me.account.id);
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = backend.fetchImpl as unknown as typeof fetch;

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
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { TeamChatScreen } = req('./TeamChatScreen') as typeof TeamChatScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  qc.setQueryData(['me'], me);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(TeamChatScreen),
        }),
      }),
    );
  });

  const findAllByTestId = (type: string, testId: string) =>
    tree.root.findAll((node) => (node.type as unknown) === type && node.props.testID === testId);

  const pressByTestId = (testId: string) => {
    const matches = findAllByTestId('Pressable', testId);
    assert.equal(matches.length, 1, `exactly one pressable with testID "${testId}"`);
    act(() => matches[0]!.props.onPress());
  };
  const typeInto = (testId: string, value: string) => {
    const matches = findAllByTestId('TextInput', testId);
    assert.equal(matches.length, 1, `exactly one TextInput with testID "${testId}"`);
    act(() => matches[0]!.props.onChangeText(value));
  };

  const flush = async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  };

  const rendered = () => JSON.stringify(tree.toJSON());
  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, qc, rendered, backend, restore, findAllByTestId, pressByTestId, typeInto, flush };
}

const SEEDED: ChatMessage[] = [
  {
    id: 'm-owner',
    workspaceId: 'ws-1',
    senderAccountId: 'acc-owner',
    body: 'hello from the owner',
    createdAt: '2026-07-27T00:00:00Z',
    editedAt: null,
    deletedAt: null,
  },
  {
    id: 'm-other',
    workspaceId: 'ws-1',
    senderAccountId: 'acc-editor',
    body: 'hello from someone else',
    createdAt: '2026-07-27T00:01:00Z',
    editedAt: null,
    deletedAt: null,
  },
];

test('own messages show edit/delete and the "You" label; other members\' messages show neither', async () => {
  const { tree, act, flush, rendered, findAllByTestId, restore } = renderScreen(SEEDED);
  await flush();

  assert.ok(rendered().includes('You'), 'own message is labeled "You"');
  assert.ok(rendered().includes('hello from someone else'), "other member's message body renders");

  assert.equal(findAllByTestId('View', 'message-row-m-owner').length, 1);
  assert.equal(
    findAllByTestId('Pressable', 'edit-message-m-owner').length,
    1,
    'own message gets an edit affordance',
  );
  assert.equal(
    findAllByTestId('Pressable', 'delete-message-m-owner').length,
    1,
    'own message gets a delete affordance',
  );
  assert.equal(
    findAllByTestId('Pressable', 'edit-message-m-other').length,
    0,
    "another member's message never gets an edit affordance",
  );
  assert.equal(
    findAllByTestId('Pressable', 'delete-message-m-other').length,
    0,
    "another member's message never gets a delete affordance",
  );

  restore();
  act(() => tree.unmount());
});

test('sending a message calls the real POST endpoint and the new message is immediately editable (it is now "own")', async () => {
  const { tree, act, flush, typeInto, pressByTestId, findAllByTestId, backend, rendered, restore } =
    renderScreen(SEEDED);
  await flush();

  typeInto('chat-message-input', 'new message from me');
  pressByTestId('send-message-button');
  await flush();

  const call = backend.calls.find((c) => c.method === 'POST' && c.path === '/workspaces/messages');
  assert.ok(call, 'the real send endpoint was called');
  assert.deepEqual(call!.body, { body: 'new message from me' });
  assert.ok(rendered().includes('new message from me'));
  assert.equal(findAllByTestId('Pressable', 'edit-message-sent-1').length, 1);

  restore();
  act(() => tree.unmount());
});

test('editing an own message calls the real PATCH endpoint and renders the corrected body with an "edited" marker', async () => {
  const { tree, act, flush, pressByTestId, typeInto, backend, rendered, restore } = renderScreen(SEEDED);
  await flush();

  pressByTestId('edit-message-m-owner');
  typeInto('edit-input-m-owner', 'corrected body');
  pressByTestId('save-edit-m-owner');
  await flush();

  const call = backend.calls.find((c) => c.method === 'PATCH' && c.path === '/workspaces/messages/m-owner');
  assert.ok(call, 'the real edit endpoint was called');
  assert.deepEqual(call!.body, { body: 'corrected body' });
  assert.ok(rendered().includes('corrected body'));
  assert.ok(rendered().includes('edited'));

  restore();
  act(() => tree.unmount());
});

test('deleting an own message calls the real DELETE endpoint and shows the redacted placeholder, with edit/delete now hidden', async () => {
  const { tree, act, flush, pressByTestId, backend, rendered, findAllByTestId, restore } = renderScreen(SEEDED);
  await flush();

  pressByTestId('delete-message-m-owner');
  await flush();

  const call = backend.calls.find((c) => c.method === 'DELETE' && c.path === '/workspaces/messages/m-owner');
  assert.ok(call, 'the real delete endpoint was called');
  assert.ok(rendered().includes('Message deleted'));
  assert.ok(!rendered().includes('hello from the owner'), 'the real body no longer renders once deleted');
  assert.equal(findAllByTestId('Pressable', 'edit-message-m-owner').length, 0, 'a deleted message loses its edit affordance');
  assert.equal(findAllByTestId('Pressable', 'delete-message-m-owner').length, 0, 'a deleted message loses its delete affordance');

  restore();
  act(() => tree.unmount());
});

test('polling passes the real cursor on the second request instead of refetching from scratch', async () => {
  const { tree, act, qc, flush, backend, restore } = renderScreen(SEEDED);
  await flush();

  const firstGet = backend.calls.find((c) => c.method === 'GET' && c.path.startsWith('/workspaces/messages'));
  assert.ok(firstGet, 'the initial fetch happened');
  assert.equal(firstGet!.path, '/workspaces/messages', 'the very first request omits since — no page fetched yet');

  await act(async () => {
    await qc.refetchQueries({ queryKey: ['workspace', 'chat', 'messages'] });
  });
  await flush();

  const gets = backend.calls.filter((c) => c.method === 'GET' && c.path.startsWith('/workspaces/messages'));
  const secondGet = gets[gets.length - 1]!;
  assert.equal(
    secondGet.path,
    '/workspaces/messages?since=m-other',
    'the second request narrows to since=<the real cursor from the first response>, not a repeat of the first request',
  );

  restore();
  act(() => tree.unmount());
});
