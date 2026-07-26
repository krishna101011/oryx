/**
 * AcceptInviteScreen — every real state GET /workspaces/invites/{token} (and
 * the accept endpoint) can produce, per services/workspaces/router.py's
 * view_invite: a found-but-resolved invite (expired/revoked/accepted) still
 * returns 200 and the client renders the real state from its fields; only a
 * genuinely unknown token 404s (INVITE_NOT_FOUND). Same harness convention
 * as TeamHomeScreen.test.tsx/PlanBillingScreen.test.tsx.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as ReactReduxNS from 'react-redux';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ReactNavigationNS from '@react-navigation/native';
import type * as StoreNS from '../../../store';
import type * as ClientNS from '../../../lib/api/client';
import type * as AcceptInviteScreenNS from './AcceptInviteScreen';
import type { WorkspaceInvite } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const TOKEN = 'test-invite-token';

function baseInvite(overrides: Partial<WorkspaceInvite> = {}): WorkspaceInvite {
  return {
    id: 'invite-1',
    workspaceId: 'ws-2',
    invitedEmail: 'invitee@oryx.test',
    role: 'editor',
    invitedBy: 'acc-owner',
    expiresAt: '2026-12-01T00:00:00Z',
    acceptedAt: null,
    revokedAt: null,
    createdAt: '2026-07-01T00:00:00Z',
    ...overrides,
  };
}

function makeFakeBackend(opts: {
  viewStatus?: number;
  invite?: WorkspaceInvite;
  acceptStatus?: number;
  acceptBody?: unknown;
}) {
  const calls: { method: string; path: string }[] = [];
  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const full = String(input);
    const path = full.replace(/^https?:\/\/[^/]+\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    calls.push({ method, path });

    if (method === 'GET' && path === `/workspaces/invites/${TOKEN}`) {
      if (opts.viewStatus && opts.viewStatus !== 200) {
        return json(
          { error: { code: 'INVITE_NOT_FOUND', message: 'Invite not found', requestId: 'rid' } },
          opts.viewStatus,
        );
      }
      return json({ data: opts.invite ?? baseInvite() });
    }
    if (method === 'POST' && path === `/workspaces/invites/${TOKEN}/accept`) {
      const status = opts.acceptStatus ?? 200;
      if (status !== 200) {
        return json(
          {
            error: {
              code: 'INVITE_EMAIL_MISMATCH',
              message: 'This invite was sent to a different email address',
              requestId: 'rid',
            },
          },
          status,
        );
      }
      return json({ data: opts.acceptBody ?? { workspaceId: 'ws-2', role: 'editor', joinedAt: '2026-07-26T00:00:00Z' } });
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls };
}

function renderScreen(opts: Parameters<typeof makeFakeBackend>[0] = {}) {
  const backend = makeFakeBackend(opts);
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

  // No real navigator needed: AcceptInviteScreen only reads route.params.token
  // and calls navigate() as a fire-and-forget side effect. The package's ESM
  // interop exports useRoute/useNavigation as non-configurable getters, so
  // neither plain assignment nor defineProperty can override them in place.
  // Instead, replace the require CACHE ENTRY with a patched copy (own
  // enumerable properties copied by value, so NavigationContainer etc. still
  // work) before AcceptInviteScreen is first required — its own require of
  // '@react-navigation/native' resolves to the same cache slot and picks up
  // the patched object.
  const navigateCalls: unknown[] = [];
  const resolvedNavPath = req.resolve('@react-navigation/native');
  const realNav = req('@react-navigation/native') as typeof ReactNavigationNS;
  const patchedNav = Object.assign(Object.create(Object.getPrototypeOf(realNav)), realNav, {
    useRoute: () => ({ params: { token: TOKEN } }),
    useNavigation: () => ({ navigate: (...args: unknown[]) => navigateCalls.push(args) }),
  });
  (req.cache![resolvedNavPath] as { exports: unknown }).exports = patchedNav;

  const { AcceptInviteScreen } = req('./AcceptInviteScreen') as typeof AcceptInviteScreenNS;

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(AcceptInviteScreen),
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

  return { tree, act, rendered, backend, restore, findAllByTestId, pressByTestId, flush, qc };
}

test('unknown token: renders the real "invite not found" state', async () => {
  const { tree, act, flush, rendered, restore } = renderScreen({ viewStatus: 404 });
  await flush();

  assert.ok(rendered().includes('Invite not found'));
  assert.ok(rendered().includes("isn't valid"));

  restore();
  act(() => tree.unmount());
});

test('revoked invite: renders the real revoked state, no accept button', async () => {
  const { tree, act, flush, rendered, findAllByTestId, restore } = renderScreen({
    invite: baseInvite({ revokedAt: '2026-07-10T00:00:00Z' }),
  });
  await flush();

  assert.ok(rendered().includes('Invite revoked'));
  assert.equal(findAllByTestId('Pressable', 'accept-invite-button').length, 0);

  restore();
  act(() => tree.unmount());
});

test('already-accepted invite: renders the real already-accepted state', async () => {
  const { tree, act, flush, rendered, restore } = renderScreen({
    invite: baseInvite({ acceptedAt: '2026-07-10T00:00:00Z' }),
  });
  await flush();

  assert.ok(rendered().includes('Already accepted'));

  restore();
  act(() => tree.unmount());
});

test('expired invite: renders the real expired state computed from expiresAt, no accept button', async () => {
  const { tree, act, flush, rendered, findAllByTestId, restore } = renderScreen({
    invite: baseInvite({ expiresAt: '2020-01-01T00:00:00Z' }),
  });
  await flush();

  assert.ok(rendered().includes('Invite expired'));
  assert.equal(findAllByTestId('Pressable', 'accept-invite-button').length, 0);

  restore();
  act(() => tree.unmount());
});

test('after accepting, "Switch to this workspace now" with no refresh token in Redux (a cookie-restored session — the real state after opening this deep link from a fresh page load) shows an honest message, never a silent no-op', async () => {
  const { tree, act, flush, rendered, pressByTestId, backend, restore } = renderScreen({
    invite: baseInvite(),
    acceptBody: { workspaceId: 'ws-2', role: 'editor', joinedAt: '2026-07-26T00:00:00Z' },
  });
  await flush();

  pressByTestId('accept-invite-button');
  await flush();
  assert.ok(rendered().includes("You're in"));

  pressByTestId('switch-to-joined-workspace');
  await flush();

  assert.equal(
    backend.calls.find((c) => c.path === '/auth/switch-workspace'),
    undefined,
    'no request fires without a real refresh token to send',
  );
  assert.ok(
    rendered().includes('Switching needs a fresh sign-in in this browser tab'),
    'the real limitation is surfaced honestly, not a silent no-op',
  );

  restore();
  act(() => tree.unmount());
});

test('valid pending invite: shows the real invitedEmail + role and an Accept button that calls the real accept endpoint', async () => {
  const { tree, act, flush, rendered, pressByTestId, backend, restore } = renderScreen({
    invite: baseInvite({ invitedEmail: 'friend@oryx.test', role: 'admin' }),
    acceptBody: { workspaceId: 'ws-2', role: 'admin', joinedAt: '2026-07-26T00:00:00Z' },
  });
  await flush();

  assert.ok(rendered().includes('friend@oryx.test'));
  assert.ok(rendered().includes('Admin'));

  pressByTestId('accept-invite-button');
  await flush();

  const acceptCall = backend.calls.find((c) => c.path === `/workspaces/invites/${TOKEN}/accept`);
  assert.ok(acceptCall, 'the real accept endpoint was called');
  assert.equal(acceptCall!.method, 'POST');
  assert.ok(rendered().includes("You're in"), 'success state renders after acceptance');
  assert.ok(rendered().includes('Admin'), 'the real granted role renders');

  restore();
  act(() => tree.unmount());
});

test('a successful accept invalidates the sidebar switcher\'s ["workspaces"]/["me"] caches — the new membership is real, so those caches must not stay stale', async () => {
  const { tree, act, flush, pressByTestId, qc, restore } = renderScreen({ invite: baseInvite() });
  await flush();

  qc.setQueryData(['workspaces'], { workspaces: [{ id: 'ws-1', name: 'Personal', kind: 'personal', role: 'owner' }] });
  qc.setQueryData(['me'], { workspace: { id: 'ws-1' } });
  assert.equal(qc.getQueryState(['workspaces'])?.isInvalidated, false);
  assert.equal(qc.getQueryState(['me'])?.isInvalidated, false);

  pressByTestId('accept-invite-button');
  await flush();

  assert.equal(
    qc.getQueryState(['workspaces'])?.isInvalidated,
    true,
    'the sidebar switcher would otherwise show a stale workspace list after a real new membership',
  );
  assert.equal(qc.getQueryState(['me'])?.isInvalidated, true);

  restore();
  act(() => tree.unmount());
});

test('a rejected accept (email mismatch) surfaces the real error, staying on the invite view', async () => {
  const { tree, act, flush, rendered, pressByTestId, restore } = renderScreen({
    invite: baseInvite(),
    acceptStatus: 403,
  });
  await flush();

  pressByTestId('accept-invite-button');
  await flush();

  assert.ok(
    rendered().includes('This invite was sent to a different email address'),
    'the real INVITE_EMAIL_MISMATCH message renders',
  );
  assert.ok(!rendered().includes("You're in"), 'no false success state');

  restore();
  act(() => tree.unmount());
});
