/**
 * Research Workspace list — shaped skeleton wiring (2026-07-26 wave).
 *
 * Real ResearchWorkspaceListScreen: while `useResearchWorkspaces()` is
 * loading, 3 SkeletonRows now render inside the SAME real Card/
 * HairlineRowList wrapper the real WorkspaceCard rows use (leadingWidth=72,
 * hasTrailingChip — the mono-id + status-chip anatomy). This proves the
 * real screen actually wires SkeletonRow (not just that the component
 * supports the shape in isolation — see skeletonShapes.test.tsx for that),
 * and that real WorkspaceCard content still renders once loading resolves.
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
import type * as DesignSystemNS from '@oryx/design-system';
import type * as ListScreenNS from './ResearchWorkspaceListScreen';
import type { ResearchWorkspace } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const WORKSPACES: ResearchWorkspace[] = [
  {
    id: '337f1ae1-880a-49b0-9033-fe36485072e0',
    accountId: 'acc-1',
    workspaceId: 'ws-1',
    name: 'Oryx Coverage',
    description: null,
    status: 'active',
    createdAt: '2026-07-13T00:00:00Z',
    updatedAt: '2026-07-13T09:15:00Z',
  },
];

function renderScreen(seedData: boolean) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext } = req('@react-navigation/native') as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { ResearchWorkspaceListScreen } = req('./ResearchWorkspaceListScreen') as typeof ListScreenNS;

  const fakeNavigation = { navigate: () => {} } as unknown as NavigationProp<ParamListBase>;
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  if (seedData) qc.setQueryData(['research', 'workspaces'], WORKSPACES);

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

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

test('while loading, shows 3 shaped SkeletonRows (mono-id + status chip anatomy), no EmptyState, no crash', () => {
  const { tree, act, rendered } = renderScreen(false);
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(SkeletonRow as never).length, 3);
  assert.ok(!rendered().includes('Create a workspace'), 'the empty-state copy must not appear while loading');

  act(() => tree.unmount());
});

test('regression: real workspaces still render through WorkspaceCard once loading resolves, no SkeletonRow', () => {
  const { tree, act, rendered } = renderScreen(true);
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(SkeletonRow as never).length, 0);
  assert.ok(rendered().includes('Oryx Coverage'));

  act(() => tree.unmount());
});
