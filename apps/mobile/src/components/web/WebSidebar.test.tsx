/**
 * WebSidebar — foot row (2026-07-25) + workspace-switcher (2026-07-26) real
 * renders. WebSidebar now calls GET /workspaces (react-query) and dispatches
 * a real POST /auth/switch-workspace thunk, so every render here needs a
 * QueryClientProvider + a configured ApiClient with a fake fetch backend, in
 * addition to the real Redux Provider already required for the foot row and
 * the signout dispatch — same harness rules as
 * PlanBillingScreen.test.tsx/catalogActivationWiring.test.tsx: register
 * shims first, monkey-patch global.fetch, load every module through the same
 * require so react-query and Redux stay one instance.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactReduxNS from 'react-redux';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as StoreNS from '../../store';
import type * as ClientNS from '../../lib/api/client';
import type * as WebSidebarNS from './WebSidebar';
import type { MeResponse, WorkspacesListResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ME: MeResponse = {
  account: {
    id: 'acc-1',
    email: 'avery@oryx.test',
    status: 'active',
    emailVerified: true,
    isPlatformAdmin: false,
    createdAt: '2026-01-01T00:00:00Z',
  },
  profile: {
    accountId: 'acc-1',
    displayName: 'Avery Solano',
    avatarUrl: null,
    headline: null,
    timezone: 'UTC',
    locale: 'en-US',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
  workspace: { id: 'ws-1', name: 'Solano Research', kind: 'personal', role: 'owner' },
  preferences: {
    accountId: 'acc-1',
    focus: 'both',
    contentStyle: 'balanced',
    verificationStrictness: 'balanced',
    notificationFrequency: 'daily',
    themeMode: 'dark',
    customTopics: [],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
  },
  activity: { unreadCount: 2 },
  flags: {
    ff_settings: true,
    ff_dashboard: true,
    ff_activity: true,
    ff_mfa: false,
    ff_research: true,
    ff_intake_gmail: false,
    ff_intake_rss: true,
    ff_intake_webhook: false,
    ff_intake_api_pull: false,
    ff_intake_manual: false,
    ff_verification: true,
    ff_content_drafts: true,
    ff_publishing_notion: false,
    ff_automation: true,
    ff_push_delivery: false,
    ff_email_delivery: false,
    ff_analytics: true,
    ff_training: false,
    ff_team_workspaces: true,
  },
  onboarding: { state: 'complete', nextStep: null },
  verification: { pendingReviewCount: 0, openConflictCount: 0, verifiedCount: 0 },
  research: { activeWorkspaceCount: 0, readyPacketCount: 0 },
  content: { draftCount: 0, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  serverTime: '2026-07-25T12:00:00Z',
  build: { version: '2.4.0', commit: 'abc123' },
};

const TWO_WORKSPACES: WorkspacesListResponse = {
  workspaces: [
    { id: 'ws-1', name: 'Solano Research', kind: 'personal', role: 'owner' },
    { id: 'ws-2', name: 'ORYX Research Team', kind: 'team', role: 'editor' },
  ],
};

function makeFakeBackend(opts: {
  workspaces?: WorkspacesListResponse;
  switchStatus?: number;
  switchBody?: unknown;
}) {
  const calls: { method: string; path: string; body: unknown }[] = [];

  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify(data), {
      status,
      headers: { 'content-type': 'application/json' },
    });

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const full = String(input);
    const path = full.replace(/^https?:\/\/[^/]+\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });

    if (method === 'GET' && path === '/workspaces') {
      return json({ data: opts.workspaces ?? { workspaces: [] } });
    }
    if (method === 'POST' && path === '/auth/switch-workspace') {
      const status = opts.switchStatus ?? 200;
      if (status !== 200) {
        // The real envelope WorkspaceNotFoundError produces (core/errors.py).
        return json(
          {
            error: {
              code: 'WORKSPACE_NOT_FOUND',
              message: 'Workspace not found or not accessible',
              requestId: 'test-request-id',
            },
          },
          status,
        );
      }
      return json({ data: opts.switchBody });
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls };
}

function renderSidebar(
  me: MeResponse | undefined,
  backendOpts: { workspaces?: WorkspacesListResponse; switchStatus?: number; switchBody?: unknown } = {},
) {
  const backend = makeFakeBackend(backendOpts);
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = backend.fetchImpl as unknown as typeof fetch;

  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-access-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { WebSidebar } = req('./WebSidebar') as typeof WebSidebarNS;

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(WebSidebar, { me, activeId: 'home', onNavigate: () => {} }),
        }),
      }),
    );
  });

  const findByTestId = (testId: string) =>
    tree.root.findAll(
      (node) =>
        (node.type as unknown) === 'Pressable' &&
        node.props.testID === testId &&
        typeof node.props.onPress === 'function',
    );

  const pressByTestId = (testId: string) => {
    const matches = findByTestId(testId);
    assert.equal(matches.length, 1, `exactly one pressable with testID "${testId}"`);
    act(() => {
      matches[0]!.props.onPress();
    });
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

  return { tree, act, pressByTestId, findByTestId, flush, rendered, backend, restore, store };
}

test('the foot row renders the real /me profile — name, initials, workspace role', async () => {
  const { tree, act, flush, rendered, restore } = renderSidebar(ME);
  await flush();
  const text = rendered();

  assert.ok(text.includes('Avery Solano'), 'real display name renders');
  assert.ok(text.includes('AS'), 'initials derived from the real name render');
  assert.ok(text.includes('OWNER'), "real workspace role ('owner' -> 'OWNER') renders");

  restore();
  act(() => tree.unmount());
});

test('the foot row never renders the design-reference "Jordan Mehta" / "EDITOR-IN-CHIEF" placeholder', async () => {
  const { tree, act, flush, rendered, restore } = renderSidebar(ME);
  await flush();
  const text = rendered();

  assert.ok(!text.includes('Jordan Mehta'), 'no hardcoded placeholder name');
  assert.ok(!text.includes('EDITOR-IN-CHIEF'), 'no hardcoded placeholder role');

  restore();
  act(() => tree.unmount());
});

test('before /me resolves (no profile yet), the foot row renders nothing rather than a fake placeholder', async () => {
  const { tree, act, flush, rendered, restore } = renderSidebar(undefined);
  await flush();
  const text = rendered();

  assert.ok(!text.includes('Jordan Mehta'));
  assert.ok(!text.includes('undefined'));

  restore();
  act(() => tree.unmount());
});

test('a cookie-restored session (no refresh token in Redux — the real state after any web page reload) shows an honest message on switch, never a silent no-op', async () => {
  const { tree, act, flush, pressByTestId, findByTestId, rendered, backend, restore } = renderSidebar(ME, {
    workspaces: TWO_WORKSPACES,
  });
  // Deliberately NOT dispatching tokensSet — this is the real state of a
  // page freshly loaded from the httpOnly access-token cookie, since web
  // never persists a refresh token the JS layer can read back (see
  // store/thunks/auth.ts persistTokens / bootstrapAuth's web branch).

  await flush();
  pressByTestId('workspace-pill');
  pressByTestId('workspace-menu-item-switch:ws-2');
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
  assert.equal(
    findByTestId('workspace-menu-item-switch:ws-2').length,
    1,
    'the menu stays open — this is not treated as a fatal error',
  );

  restore();
  act(() => tree.unmount());
});

test('the workspace pill lists a real second workspace and switching calls the real backend, closing the menu on success', async () => {
  const { tree, act, flush, pressByTestId, findByTestId, rendered, backend, restore, store } = renderSidebar(ME, {
    workspaces: TWO_WORKSPACES,
    switchBody: {
      accessToken: 'new-access-token',
      refreshToken: 'new-refresh-token',
      accessTokenExpiresAt: '2026-07-26T13:00:00Z',
      refreshTokenExpiresAt: '2026-08-25T12:00:00Z',
      sessionId: 'sess-2',
      accountId: 'acc-1',
    },
  });

  // Seed a real refresh token into the live store — switchWorkspace reads it
  // via useAppSelector, exactly like a signed-in session would carry one.
  const { authActions } = req('../../store/slices/auth') as { authActions: { tokensSet: (t: unknown) => unknown } };
  act(() => {
    store.dispatch(
      authActions.tokensSet({
        accessToken: 'old-access-token',
        refreshToken: 'refresh-1',
        accessTokenExpiresAt: '2026-07-26T12:15:00Z',
        refreshTokenExpiresAt: '2026-08-25T12:00:00Z',
        sessionId: 'sess-1',
        accountId: 'acc-1',
      }) as never,
    );
  });

  await flush();
  pressByTestId('workspace-pill');

  const opened = rendered();
  assert.ok(opened.includes('ORYX Research Team'), 'the real other workspace name renders');
  assert.ok(opened.includes('Team · Editor'), 'its real kind + role renders as the sub-label');

  pressByTestId('workspace-menu-item-switch:ws-2');
  await flush();

  const switchCall = backend.calls.find((c) => c.path === '/auth/switch-workspace');
  assert.ok(switchCall, 'the real switch-workspace endpoint was called');
  assert.equal(switchCall!.method, 'POST');
  const switchBody = switchCall!.body as { refreshToken: string; deviceId: string; workspaceId: string };
  assert.deepEqual(switchBody, { refreshToken: 'refresh-1', deviceId: switchBody.deviceId, workspaceId: 'ws-2' });

  assert.ok(
    findByTestId('workspace-menu-item-account').length === 0,
    'the dropdown closes after a successful switch',
  );

  const { authActions: authActionsForReset } = req('../../store/slices/auth') as {
    authActions: { signedOut: () => unknown };
  };
  act(() => store.dispatch(authActionsForReset.signedOut() as never));
  restore();
  act(() => tree.unmount());
});

test('a rejected switch surfaces the real error message and leaves the menu open', async () => {
  const { tree, act, flush, pressByTestId, findByTestId, rendered, restore, store } = renderSidebar(ME, {
    workspaces: TWO_WORKSPACES,
    switchStatus: 404,
  });

  const { authActions } = req('../../store/slices/auth') as { authActions: { tokensSet: (t: unknown) => unknown; signedOut: () => unknown } };
  act(() => {
    store.dispatch(
      authActions.tokensSet({
        accessToken: 'old-access-token',
        refreshToken: 'refresh-1',
        accessTokenExpiresAt: '2026-07-26T12:15:00Z',
        refreshTokenExpiresAt: '2026-08-25T12:00:00Z',
        sessionId: 'sess-1',
        accountId: 'acc-1',
      }) as never,
    );
  });

  await flush();
  pressByTestId('workspace-pill');
  pressByTestId('workspace-menu-item-switch:ws-2');
  await flush();

  const after = rendered();
  assert.ok(after.includes('Sign out'), 'the menu stays open after a failed switch');
  assert.ok(
    after.includes('Workspace not found or not accessible'),
    'the real WORKSPACE_NOT_FOUND message renders, not a generic failure string',
  );
  assert.ok(
    findByTestId('workspace-menu-item-switch:ws-2').length === 1,
    'the switch item is still there to retry',
  );

  act(() => store.dispatch(authActions.signedOut() as never));
  restore();
  act(() => tree.unmount());
});
