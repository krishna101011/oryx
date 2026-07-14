/**
 * Rendered-press regression for the Research Workspace list rows (2026-07-14
 * sign-off ask). The pure-logic suite proves the presenters; THIS test proves
 * the wiring the presenters can't see: a real render of the real
 * ResearchWorkspaceListScreen + WorkspaceCard, a press on a rendered row, and
 * an assertion that navigation fires to ResearchWorkspaceDetail carrying that
 * row's own rwsId.
 *
 * Only the platform layer (react-native, svg, blur, lucide, safe-area) is
 * shimmed to inert prop-forwarding hosts (src/test/shims/) — every ORYX-owned
 * module in the chain (screen, WorkspaceCard, design-system Pressable/Card/
 * HairlineRowList, react-query, react-navigation's context) runs for real.
 * The shims must be registered before anything that imports react-native, so
 * all component loads below go through req() after registration. req() is
 * also load-bearing for module identity: dynamic import() would pull the ESM
 * builds of react-query/react-navigation while the product code (CJS under
 * tsx) uses the CJS builds — two context instances, provider invisible to the
 * hook. One require function keeps the whole graph on one instance.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactNavigationNS from '@react-navigation/native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ListScreenNS from './screens/ResearchWorkspaceListScreen';
import type { ResearchWorkspace } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

// react-test-renderer's act() checks this flag under React 18.
(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

/** The live workspace's actual uuid (same fixture id list.test.ts pins). */
const LIVE_ID = '337f1ae1-880a-49b0-9033-fe36485072e0';
const SECOND_ID = '9b2c4d6e-1f3a-4b5c-8d7e-0a1b2c3d4e5f';

const workspace = (id: string, name: string): ResearchWorkspace => ({
  id,
  accountId: 'acc-1',
  workspaceId: 'ws-1',
  name,
  description: null,
  status: 'active',
  createdAt: '2026-07-13T00:00:00Z',
  updatedAt: '2026-07-13T09:15:00Z',
});

const WORKSPACES = [
  workspace(LIVE_ID, 'Oryx Coverage'),
  workspace(SECOND_ID, 'Rates Desk Notes'),
];

function renderListScreen() {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext } = req(
    '@react-navigation/native',
  ) as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { ResearchWorkspaceListScreen } = req(
    './screens/ResearchWorkspaceListScreen',
  ) as typeof ListScreenNS;

  const navigateCalls: Array<{ name: string; params: unknown }> = [];
  const fakeNavigation = {
    navigate: (name: string, params?: unknown) => {
      navigateCalls.push({ name, params });
    },
  } as unknown as NavigationProp<ParamListBase>;

  // Seed the exact query key useResearchWorkspaces reads; staleTime Infinity
  // keeps the mount from refetching, so no network is touched.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['research', 'workspaces'], WORKSPACES);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          NavigationContext.Provider,
          { value: fakeNavigation },
          React.createElement(ResearchWorkspaceListScreen),
        ),
      ),
    );
  });

  /** The rendered row's pressable, located by its accessibility contract. */
  const rowPressable = (name: string) => {
    const matches = tree.root.findAll(
      (node) =>
        (node.type as unknown) === 'Pressable' &&
        node.props.accessibilityRole === 'button' &&
        node.props.accessibilityLabel === name &&
        typeof node.props.onPress === 'function',
    );
    assert.equal(matches.length, 1, `exactly one pressable row named "${name}"`);
    return matches[0]!;
  };

  const press = (name: string) => {
    act(() => {
      rowPressable(name).props.onPress();
    });
  };

  return { tree, act, navigateCalls, press };
}

test("pressing a rendered workspace row navigates to ResearchWorkspaceDetail with that row's real rwsId", () => {
  const { tree, act, navigateCalls, press } = renderListScreen();

  press('Oryx Coverage');
  assert.deepEqual(navigateCalls, [
    { name: 'ResearchWorkspaceDetail', params: { rwsId: LIVE_ID } },
  ]);

  act(() => tree.unmount());
});

test('each row carries its OWN id — two rows, two presses, two distinct rwsIds in order', () => {
  const { tree, act, navigateCalls, press } = renderListScreen();

  press('Rates Desk Notes');
  press('Oryx Coverage');
  assert.deepEqual(navigateCalls, [
    { name: 'ResearchWorkspaceDetail', params: { rwsId: SECOND_ID } },
    { name: 'ResearchWorkspaceDetail', params: { rwsId: LIVE_ID } },
  ]);

  act(() => tree.unmount());
});
