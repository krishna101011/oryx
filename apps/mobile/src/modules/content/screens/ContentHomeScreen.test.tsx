/**
 * Content Studio home — shaped skeleton wiring (2026-07-26 wave).
 *
 * Real ContentHomeScreen: while `useDraftList()` is loading, 3 SkeletonRows
 * now render inside the SAME real Card/HairlineRowList wrapper the real
 * DraftCard rows use (leadingWidth=80, hasTrailingChip — the fixed
 * date-column + status-chip anatomy). Proves the real screen wires
 * SkeletonRow, and that real DraftCard content still renders once loading
 * resolves.
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
import type * as ContentScreenNS from './ContentHomeScreen';
import type { ContentDraft } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const DRAFTS: ContentDraft[] = [
  {
    id: 'draft-1',
    workspaceId: 'ws-1',
    accountId: 'acc-1',
    packetId: 'packet-1',
    templateId: null,
    format: 'article',
    title: 'Fed holds rates steady — what it means',
    status: 'draft',
    currentVersion: 1,
    generationModel: 'claude',
    wordCount: 420,
    publishedAt: null,
    createdAt: '2026-07-25T10:00:00Z',
    updatedAt: '2026-07-25T10:00:00Z',
  } as ContentDraft,
];

function renderScreen(seedData: boolean) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext } = req('@react-navigation/native') as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { ContentHomeScreen } = req('./ContentHomeScreen') as typeof ContentScreenNS;

  const fakeNavigation = { navigate: () => {} } as unknown as NavigationProp<ParamListBase>;
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  if (seedData) qc.setQueryData(['content', 'drafts'], DRAFTS);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          NavigationContext.Provider,
          { value: fakeNavigation },
          React.createElement(ContentHomeScreen),
        ),
      ),
    );
  });

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

test('while loading, shows 3 shaped SkeletonRows (date-column + status chip anatomy), no EmptyState, no crash', () => {
  const { tree, act, rendered } = renderScreen(false);
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(SkeletonRow as never).length, 3);
  assert.ok(!rendered().includes('Start your first draft'), 'the empty-state copy must not appear while loading');

  act(() => tree.unmount());
});

test('regression: real drafts still render through DraftCard once loading resolves, no SkeletonRow', () => {
  const { tree, act, rendered } = renderScreen(true);
  const { SkeletonRow } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(tree.root.findAllByType(SkeletonRow as never).length, 0);
  assert.ok(rendered().includes('Fed holds rates steady'));

  act(() => tree.unmount());
});
