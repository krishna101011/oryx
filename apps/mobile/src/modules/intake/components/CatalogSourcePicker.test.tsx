/**
 * CatalogSourcePicker loading-vs-empty conflation fix (2026-07-25).
 *
 * Both real callers (TrustedSourcesScreen, FocusAndSourcesScreen) pass
 * `catalog={query.data ?? []}` — before this fix, an in-flight catalog fetch
 * and a (never-real-in-practice) empty catalog rendered IDENTICALLY: nothing
 * at all. `isLoading` now gates a generic Skeleton so loading is visually
 * distinguishable from empty. Pure prop-level render — no query client or
 * navigation needed, this component only ever reads its own props.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as DesignSystemNS from '@oryx/design-system';
import type * as PickerNS from './CatalogSourcePicker';
import type { SourceCatalogEntry } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const CATALOG: SourceCatalogEntry[] = [
  { key: 'coindesk', name: 'CoinDesk', url: 'https://www.coindesk.com/arc/outboundfeeds/rss/', focus: 'crypto', editorialConfidence: 78 },
];

function render(props: Partial<PickerNS.CatalogSourcePickerProps> = {}) {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { CatalogSourcePicker } = req('./CatalogSourcePicker') as typeof PickerNS;

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(CatalogSourcePicker, {
        catalog: [],
        activationMap: {},
        onToggle: () => {},
        ...props,
      }),
    );
  });

  return { tree, act };
}

function findSkeleton(tree: ReactTestRenderer) {
  const { Skeleton } = req('@oryx/design-system') as typeof DesignSystemNS;
  return tree.root.findAllByType(Skeleton as never);
}

test('isLoading: true renders a Skeleton, not a blank view — even with a real catalog available', () => {
  const { tree, act } = render({ catalog: CATALOG, isLoading: true });

  assert.equal(findSkeleton(tree).length, 1, 'exactly one Skeleton renders');
  assert.ok(!JSON.stringify(tree.toJSON()).includes('CoinDesk'), 'no tile renders while loading');

  act(() => tree.unmount());
});

test('isLoading: false with a real catalog renders the real tiles, no Skeleton', () => {
  const { tree, act } = render({ catalog: CATALOG, isLoading: false });

  assert.equal(findSkeleton(tree).length, 0, 'no Skeleton once loaded');
  assert.ok(JSON.stringify(tree.toJSON()).includes('CoinDesk'), 'the real tile renders');

  act(() => tree.unmount());
});

test('isLoading: false with a genuinely empty catalog renders nothing (no Skeleton, no crash) — the pre-existing, unchanged empty behavior', () => {
  const { tree, act } = render({ catalog: [], isLoading: false });

  assert.equal(findSkeleton(tree).length, 0);
  const json = tree.toJSON() as { children: unknown[] | null } | null;
  assert.ok(json !== null && !Array.isArray(json), 'the outer View still mounts, as a single root');
  assert.equal(json!.children, null, 'the empty-catalog View has no rendered children');

  act(() => tree.unmount());
});
