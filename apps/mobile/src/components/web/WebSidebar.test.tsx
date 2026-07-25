/**
 * WebSidebar foot row — real-render regression (2026-07-25).
 *
 * Locks in what recon confirmed was already true of the shipped code (no fix
 * needed here, unlike the IntakeItemDetail back-nav bug this same wave
 * fixes): the foot row renders the REAL /me profile (display name, initials,
 * workspace role) via the same `me` prop the rest of the sidebar reads, not
 * a hardcoded "Jordan Mehta" placeholder (docs/design-reference/app.jsx's
 * static mock — never a real data source). Real component, real Redux
 * Provider (WebSidebar dispatches signout() through useAppDispatch), only
 * the platform layer shimmed — same convention as rowNavigation.test.tsx /
 * catalogActivationWiring.test.tsx.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactReduxNS from 'react-redux';
import type * as StoreNS from '../../store';
import type * as WebSidebarNS from './WebSidebar';
import type { MeResponse } from '@oryx/shared-types';

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
    ff_team_workspaces: false,
  },
  onboarding: { state: 'complete', nextStep: null },
  verification: { pendingReviewCount: 0, openConflictCount: 0, verifiedCount: 0 },
  research: { activeWorkspaceCount: 0, readyPacketCount: 0 },
  content: { draftCount: 0, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  serverTime: '2026-07-25T12:00:00Z',
  build: { version: '2.4.0', commit: 'abc123' },
};

function renderSidebar(me?: MeResponse) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { Provider } = req('react-redux') as typeof ReactReduxNS;
  const { store } = req('../../store') as typeof StoreNS;
  const { WebSidebar } = req('./WebSidebar') as typeof WebSidebarNS;

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(WebSidebar, { me, activeId: 'home', onNavigate: () => {} }),
      }),
    );
  });

  const rendered = () => JSON.stringify(tree.toJSON());
  return { tree, act, rendered };
}

test('the foot row renders the real /me profile — name, initials, workspace role', () => {
  const { tree, act, rendered } = renderSidebar(ME);
  const text = rendered();

  assert.ok(text.includes('Avery Solano'), 'real display name renders');
  assert.ok(text.includes('AS'), 'initials derived from the real name render');
  assert.ok(text.includes('OWNER'), "real workspace role ('owner' -> 'OWNER') renders");

  act(() => tree.unmount());
});

test('the foot row never renders the design-reference "Jordan Mehta" / "EDITOR-IN-CHIEF" placeholder', () => {
  const { tree, act, rendered } = renderSidebar(ME);
  const text = rendered();

  assert.ok(!text.includes('Jordan Mehta'), 'no hardcoded placeholder name');
  assert.ok(!text.includes('EDITOR-IN-CHIEF'), 'no hardcoded placeholder role');

  act(() => tree.unmount());
});

test('before /me resolves (no profile yet), the foot row renders nothing rather than a fake placeholder', () => {
  const { tree, act, rendered } = renderSidebar(undefined);
  const text = rendered();

  assert.ok(!text.includes('Jordan Mehta'));
  assert.ok(!text.includes('undefined'));

  act(() => tree.unmount());
});
