/**
 * The isolation proof this wave cares about most: a public reader link must
 * never show authenticated-app chrome (sidebar, topbar, account info), even
 * for a visitor who ALREADY has a live authenticated session in the same
 * browser tab (e.g. they open a public link while already signed in) — and
 * the reverse must keep working: a real authenticated, fully-onboarded
 * session on a normal route still gets its real chrome.
 *
 * Before this wave, WebShellInner computed `showChrome` from auth.status +
 * me.data alone, with no notion of "are we on a public route" — so an
 * already-authenticated visitor opening a public link would have seen their
 * own sidebar/topbar wrapped around the public page. This test renders the
 * real WebShell with a real authenticated Redux store + seeded /me cache,
 * toggling only window.location.pathname between a public-page path and a
 * normal one, and asserts the sidebar's own real accessibility contract
 * (WebSidebar's 'workspace-pill' testID, per WebSidebar.test.tsx) appears
 * only when it should.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as ReactReduxNS from 'react-redux';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as StoreNS from '../../store';
import type * as ClientNS from '../../lib/api/client';
import type * as WebShellNS from './WebShell';
import type { MeResponse } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

// A COMPLETE MeResponse, not a minimal ad hoc one — WebSidebar (mounted
// whenever chrome shows) reads several fields with only ONE level of
// optional chaining (`me?.profile.displayName`, `me?.build.version`,
// `me?.verification.pendingReviewCount` in webNav.ts's navCounts) — a
// partial fixture crashes the render rather than showing zero/blank badges.
// Same shape as WebSidebar.test.tsx's own ME fixture.
const ME_COMPLETE: MeResponse = {
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
  activity: { unreadCount: 0 },
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
  serverTime: '2026-08-01T12:00:00Z',
  build: { version: '2.4.0', commit: 'abc123' },
};

// Installed ONCE for the whole file, never deleted between tests: WebSidebar
// fires an async ['workspaces'] query whose resolution can land after a
// test's own synchronous assertions (and even after a later test's setup),
// since nothing here awaits react-query settling. Deleting `window`/
// `document` between tests raced that trailing async work — a stray
// `document.addEventListener` call from a still-settling effect could fire
// against a `document` an earlier test had already deleted. A stub that
// simply persists for the file's lifetime removes the race entirely.
const windowStub = { location: { pathname: '/' } };
(globalThis as unknown as { window: unknown }).window = windowStub;
(globalThis as unknown as { document: unknown }).document = {
  addEventListener: () => {},
  removeEventListener: () => {},
};

function setWindowPath(pathname: string): void {
  windowStub.location.pathname = pathname;
}

function renderShell(opts: { authenticated: boolean; pathname: string }) {
  setWindowPath(opts.pathname);

  // WebSidebar (mounted whenever chrome shows) calls apiClient().get('/workspaces')
  // from its own queryFn — configure a harmless fake so that query fails
  // cleanly instead of throwing "ApiClient not configured" (this test isn't
  // exercising the workspace switcher, just the chrome-visibility branch).
  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => null,
    getWorkspaceId: () => null,
    refreshAccessToken: async () => null,
  });
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (async () =>
    new Response(JSON.stringify({ data: { workspaces: [] } }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })) as unknown as typeof fetch;

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { WebShell } = req('./WebShell') as typeof WebShellNS;

  if (opts.authenticated) {
    const { authActions } = req('../../store/slices/auth') as {
      authActions: { tokensSet: (t: unknown) => unknown };
    };
    act(() => {
      store.dispatch(
        authActions.tokensSet({
          accessToken: 'test-access-token',
          refreshToken: 'test-refresh-token',
          accountId: 'acc-1',
          sessionId: 'sess-1',
          accessTokenExpiresAt: '2099-01-01T00:00:00Z',
        }) as never,
      );
    });
  }

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['me'], ME_COMPLETE);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(
            WebShell,
            null,
            React.createElement('PublicPageContentMarker', null),
          ),
        }),
      }),
    );
  });

  const hasSidebar = () =>
    tree.root.findAll(
      (node) => node.props.testID === 'workspace-pill',
    ).length > 0;
  const hasMarker = () =>
    tree.root.findAll((node) => (node.type as unknown) === 'PublicPageContentMarker').length > 0;

  const reset = () => {
    const { authActions } = req('../../store/slices/auth') as { authActions: { signedOut: () => unknown } };
    act(() => store.dispatch(authActions.signedOut() as never));
    setWindowPath('/');
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, hasSidebar, hasMarker, reset };
}

test('an authenticated, fully-onboarded visitor on a PUBLIC route sees no sidebar chrome', () => {
  const { tree, act, hasSidebar, hasMarker, reset } = renderShell({
    authenticated: true,
    pathname: '/public/pages/q3-earnings-recap',
  });

  assert.equal(hasSidebar(), false, 'no authenticated chrome around a public page, even when signed in');
  assert.equal(hasMarker(), true, 'the public page content itself still renders, full-bleed');

  reset();
  act(() => tree.unmount());
});

test('the SAME authenticated session on a NORMAL route still gets its real chrome (regression guard)', () => {
  const { tree, act, hasSidebar, hasMarker, reset } = renderShell({
    authenticated: true,
    pathname: '/home',
  });

  assert.equal(hasSidebar(), true, 'chrome must still render for a real authenticated, non-public route');
  assert.equal(hasMarker(), true);

  reset();
  act(() => tree.unmount());
});

test('an unauthenticated visitor on a public route also sees no chrome (baseline)', () => {
  const { tree, act, hasSidebar, hasMarker, reset } = renderShell({
    authenticated: false,
    pathname: '/public/pages/q3-earnings-recap',
  });

  assert.equal(hasSidebar(), false);
  assert.equal(hasMarker(), true);

  reset();
  act(() => tree.unmount());
});
