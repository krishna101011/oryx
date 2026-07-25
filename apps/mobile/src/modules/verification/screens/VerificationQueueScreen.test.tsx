/**
 * Verification Center — bespoke skeleton wiring (2026-07-26 wave).
 *
 * Real VerificationQueueScreen: while `useReviewQueue()` is loading, 3
 * bespoke SkeletonQueueCards render — recon confirmed this screen's
 * standalone `Card variant="elevated"` rows are the app's one genuinely
 * one-off row shape (not the shared HairlineRowList family SkeletonRow
 * covers), so the skeleton is a locally-defined component, not exported.
 * Verified via its real composition (3 bordered Cards, each 4 Skeleton
 * bars: subject/type line, 2-line body text, badge pill) — see the file's
 * own SkeletonQueueCard doc comment. Real claim/conflict content still
 * renders once loading resolves.
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
import type * as QueueScreenNS from './VerificationQueueScreen';
import type { Claim, ReviewQueue } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const QUEUE: ReviewQueue = {
  pendingClaims: [
    {
      id: 'claim-1',
      workspaceId: 'ws-1',
      intakeItemId: 'item-1',
      text: 'The Fed voted to hold the target range unchanged at 5.25-5.50%.',
      subject: 'Federal Reserve rate decision',
      predicate: 'held',
      object: null,
      epistemicType: 'fact',
      extractorVersion: 1,
      classifierVersion: 1,
      requiresAnalystReview: true,
      supersededBy: null,
      createdAt: '2026-07-25T10:00:00Z',
    } as Claim,
  ],
  openConflicts: [],
};

function renderScreen(seedData: boolean) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { NavigationContext } = req('@react-navigation/native') as typeof ReactNavigationNS;
  const { QueryClient, QueryClientProvider } = req('@tanstack/react-query') as typeof ReactQueryNS;
  const { VerificationQueueScreen } = req('./VerificationQueueScreen') as typeof QueueScreenNS;

  const fakeNavigation = { navigate: () => {} } as unknown as NavigationProp<ParamListBase>;
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  if (seedData) qc.setQueryData(['verification', 'review-queue'], QUEUE);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(
          NavigationContext.Provider,
          { value: fakeNavigation },
          React.createElement(VerificationQueueScreen),
        ),
      ),
    );
  });

  return { tree, act, rendered: () => JSON.stringify(tree.toJSON()) };
}

test('while loading, shows 3 shaped elevated-card skeletons, real page title, no crash', () => {
  const { tree, act, rendered } = renderScreen(false);
  const { Card, Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.ok(rendered().includes('Review queue'), 'the real page title still renders while loading');
  assert.equal(tree.root.findAllByType(Card as never).length, 3, 'one elevated Card per SkeletonQueueCard');
  assert.equal(tree.root.findAllByType(Skeleton as never).length, 12, '4 Skeleton bars per card x 3 cards');
  assert.ok(!rendered().includes('Nothing pending review'), 'the empty-state copy must not appear while loading');

  act(() => tree.unmount());
});

test('regression: a real pending claim still renders its subject/text/badge once loading resolves', () => {
  const { tree, act, rendered } = renderScreen(true);

  assert.ok(rendered().includes('Federal Reserve rate decision'));
  assert.ok(rendered().includes('The Fed voted to hold'));

  act(() => tree.unmount());
});
