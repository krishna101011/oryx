/**
 * TeamHomeScreen — real Card/CardHeader/HairlineRowList + react-query pattern,
 * same harness convention as PlanBillingScreen.test.tsx/DashboardScreen.test.tsx.
 * Moved verbatim from MembersScreen.test.tsx (Team promotion wave, 2026-07-26)
 * plus new coverage for the real recent-activity preview and its "View all
 * activity" link into TeamActivityScreen.
 *
 * The role-restriction tests exist because CAPABILITIES["editor"|"reader"]
 * (core/dependencies.py) never grant workspace.manage — only owner/admin do —
 * so this screen must never show invite/remove controls to a role the
 * backend would 403 anyway, and must never let ANY role invite someone as
 * 'owner' (InviteRole excludes it at the type level; the UI must too).
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
import type * as TeamHomeScreenNS from './TeamHomeScreen';
import type {
  MeResponse,
  WorkspaceActivityListResponse,
  WorkspaceInvite,
  WorkspaceInvitesListResponse,
  WorkspaceMemberSummary,
} from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const ME_OWNER = { workspace: { id: 'ws-1', role: 'owner' }, account: { id: 'acc-owner' } } as unknown as MeResponse;
const ME_EDITOR = { workspace: { id: 'ws-1', role: 'editor' }, account: { id: 'acc-editor' } } as unknown as MeResponse;

const MEMBERS: WorkspaceMemberSummary[] = [
  { accountId: 'acc-owner', role: 'owner', joinedAt: '2026-01-01T00:00:00Z' },
  { accountId: 'acc-editor', role: 'editor', joinedAt: '2026-02-01T00:00:00Z' },
];

const NO_INVITES: WorkspaceInvitesListResponse = { invites: [] };
const NO_ACTIVITY: WorkspaceActivityListResponse = { events: [] };

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

function makeFakeBackend() {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify({ data }), { status, headers: { 'content-type': 'application/json' } });

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const full = String(input);
    const path = full.replace(/^https?:\/\/[^/]+\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });

    if (method === 'POST' && path === '/workspaces/invites') {
      const invite: WorkspaceInvite = {
        id: 'invite-new',
        workspaceId: 'ws-1',
        invitedEmail: (body as { email: string }).email,
        role: (body as { role: WorkspaceInvite['role'] }).role,
        invitedBy: 'acc-owner',
        expiresAt: '2026-08-02T00:00:00Z',
        acceptedAt: null,
        revokedAt: null,
        createdAt: '2026-07-26T00:00:00Z',
      };
      return json(invite);
    }
    if (method === 'POST' && /\/workspaces\/invites\/.+\/revoke$/.test(path)) {
      return json({ revoked: true });
    }
    if (method === 'DELETE' && /\/workspaces\/members\/.+$/.test(path)) {
      return json({ removed: true });
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls };
}

function renderScreen(
  me: MeResponse,
  invites: WorkspaceInvitesListResponse = NO_INVITES,
  activity: WorkspaceActivityListResponse = NO_ACTIVITY,
) {
  const backend = makeFakeBackend();
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
  const { NavigationContext } = req('@react-navigation/native') as typeof ReactNavigationNS;
  const { TeamHomeScreen } = req('./TeamHomeScreen') as typeof TeamHomeScreenNS;

  setAuthenticated(store);

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  qc.setQueryData(['me'], me);
  qc.setQueryData(['workspace', 'members'], MEMBERS);
  qc.setQueryData(['workspace', 'invites'], invites);
  qc.setQueryData(['workspace', 'activity'], activity);

  // NavigationContext.Provider (not a require-cache patch on useNavigation):
  // a module-level patch only takes effect for the FIRST render in this file
  // to require TeamHomeScreen — its already-bound `useNavigation` reference
  // keeps pointing at that first patch's closure on every later renderScreen()
  // call in this same test file (same convention as
  // research/rowNavigation.test.tsx).
  const navigateCalls: unknown[][] = [];
  const fakeNavigation = {
    navigate: (...args: unknown[]) => navigateCalls.push(args),
  } as unknown as ReactNavigationNS.NavigationProp<ReactNavigationNS.ParamListBase>;

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(Provider, {
        store,
        children: React.createElement(QueryClientProvider, {
          client: qc,
          children: React.createElement(NavigationContext.Provider, {
            value: fakeNavigation,
            children: React.createElement(TeamHomeScreen),
          }),
        }),
      }),
    );
  });

  const findAllByTestId = (type: string, testId: string) =>
    tree.root.findAll((node) => (node.type as unknown) === type && node.props.testID === testId);
  const findAllByLabel = (type: string, label: string) =>
    tree.root.findAll((node) => (node.type as unknown) === type && node.props.accessibilityLabel === label);

  const pressByTestId = (testId: string) => {
    const matches = findAllByTestId('Pressable', testId);
    assert.equal(matches.length, 1, `exactly one pressable with testID "${testId}"`);
    act(() => matches[0]!.props.onPress());
  };
  const pressByLabel = (label: string) => {
    const matches = findAllByLabel('Pressable', label);
    assert.equal(matches.length, 1, `exactly one pressable labeled "${label}"`);
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

  return {
    tree,
    act,
    rendered,
    backend,
    navigateCalls,
    restore,
    findAllByTestId,
    findAllByLabel,
    pressByTestId,
    pressByLabel,
    typeInto,
    flush,
  };
}

test('page title is now "Team", not "Members" — the section landing screen, not a Settings sub-screen', () => {
  const { tree, act, rendered, restore } = renderScreen(ME_OWNER);
  assert.ok(rendered().includes('Team'));
  restore();
  act(() => tree.unmount());
});

test('as owner: invite roles offered are exactly Admin/Editor/Reader — never Owner', () => {
  const { tree, act, findAllByLabel, restore } = renderScreen(ME_OWNER);

  assert.equal(findAllByLabel('Pressable', 'Admin').length, 1);
  assert.equal(findAllByLabel('Pressable', 'Editor').length, 1);
  assert.equal(findAllByLabel('Pressable', 'Reader').length, 1);
  assert.equal(findAllByLabel('Pressable', 'Owner').length, 0, 'Owner is never an offered invite role');

  restore();
  act(() => tree.unmount());
});

test('as owner: can remove the non-owner member but not the owner row', () => {
  const { tree, act, findAllByTestId, restore } = renderScreen(ME_OWNER);

  assert.equal(
    findAllByTestId('Pressable', 'remove-member-acc-editor').length,
    1,
    'a non-owner member is removable',
  );
  assert.equal(
    findAllByTestId('Pressable', 'remove-member-acc-owner').length,
    0,
    'the owner row never gets a Remove control',
  );

  restore();
  act(() => tree.unmount());
});

test('as editor (no workspace.manage): read-only member list, no invite form, no remove controls', () => {
  const { tree, act, rendered, findAllByTestId, restore } = renderScreen(ME_EDITOR);

  assert.ok(
    rendered().includes('Only workspace owners and admins can invite or remove members'),
    'the honest read-only explanation renders',
  );
  assert.equal(findAllByTestId('Pressable', 'send-invite-button').length, 0);
  assert.equal(findAllByTestId('Pressable', 'remove-member-acc-editor').length, 0);
  assert.equal(findAllByTestId('Pressable', 'remove-member-acc-owner').length, 0);

  restore();
  act(() => tree.unmount());
});

test('sending an invite calls the real create-invite endpoint with the picked role, then clears the email field', async () => {
  const { tree, act, flush, typeInto, pressByLabel, pressByTestId, findAllByTestId, backend, restore } =
    renderScreen(ME_OWNER);

  typeInto('invite-email-input', 'friend@oryx.test');
  pressByLabel('Admin');
  pressByTestId('send-invite-button');
  await flush();

  const call = backend.calls.find((c) => c.path === '/workspaces/invites' && c.method === 'POST');
  assert.ok(call, 'the real create-invite endpoint was called');
  assert.deepEqual(call!.body, { email: 'friend@oryx.test', role: 'admin' });

  const emailInput = findAllByTestId('TextInput', 'invite-email-input')[0]!;
  assert.equal(emailInput.props.value, '', 'the email field clears after a successful invite');

  restore();
  act(() => tree.unmount());
});

test('revoking a pending invite calls the real revoke endpoint', async () => {
  const invites: WorkspaceInvitesListResponse = {
    invites: [
      {
        id: 'invite-1',
        workspaceId: 'ws-1',
        invitedEmail: 'pending@oryx.test',
        role: 'reader',
        invitedBy: 'acc-owner',
        expiresAt: '2026-12-01T00:00:00Z',
        acceptedAt: null,
        revokedAt: null,
        createdAt: '2026-07-26T00:00:00Z',
      },
    ],
  };
  const { tree, act, flush, pressByTestId, rendered, backend, restore } = renderScreen(ME_OWNER, invites);

  assert.ok(rendered().includes('pending@oryx.test'), 'the real pending invite renders');

  pressByTestId('revoke-invite-invite-1');
  await flush();

  const call = backend.calls.find((c) => c.path === '/workspaces/invites/invite-1/revoke');
  assert.ok(call, 'the real revoke endpoint was called');
  assert.equal(call!.method, 'POST');

  restore();
  act(() => tree.unmount());
});

test('no activity yet: no "Recent activity" card renders at all (honest empty state, no fake placeholder)', () => {
  const { tree, act, rendered, findAllByTestId, restore } = renderScreen(ME_OWNER, NO_INVITES, NO_ACTIVITY);
  assert.ok(!rendered().includes('Recent activity'));
  assert.equal(findAllByTestId('Pressable', 'view-all-activity-button').length, 0);
  restore();
  act(() => tree.unmount());
});

test('real activity renders in the Recent activity preview, and "View all activity" navigates to TeamActivity', () => {
  const activity: WorkspaceActivityListResponse = {
    events: [
      {
        id: 'evt-1',
        event: 'member_joined',
        actorAccountId: 'acc-editor',
        subjectAccountId: 'acc-editor',
        subjectEmail: null,
        role: 'editor',
        createdAt: '2026-07-26T12:00:00Z',
      },
    ],
  };
  const { tree, act, rendered, pressByTestId, navigateCalls, restore } = renderScreen(
    ME_OWNER,
    NO_INVITES,
    activity,
  );

  assert.ok(rendered().includes('joined as Editor'), 'the real event renders in the preview');

  pressByTestId('view-all-activity-button');
  assert.deepEqual(navigateCalls[0], ['TeamActivity']);

  restore();
  act(() => tree.unmount());
});
