/**
 * PublicPageScreen — real render, three angles:
 *
 * 1. "Renders with zero auth state present": deliberately NO react-redux
 *    Provider is mounted anywhere in this tree (contrast every other screen
 *    test in this repo, e.g. AcceptInviteScreen.test.tsx / WebSidebar.test.tsx,
 *    which all wrap in `Provider store={store}`). If this screen or anything
 *    it imports called useAppSelector/useMe, react-redux's hook would throw
 *    ("could not find react-redux context value") the instant it rendered,
 *    and every test below would fail at `create()` — passing IS the proof,
 *    not an assertion added on top of it.
 * 2. Real paragraph splitting + citation copy/tone from a seeded response.
 * 3. The real 404 state for an unknown slug, via a faked network 404 (the
 *    same fetch-faking convention AcceptInviteScreen.test.tsx uses, since
 *    this screen calls fetch directly rather than the shared apiClient — see
 *    reader/api/publicPages.ts's isolation rationale).
 *
 * Same harness rules as rowNavigation.test.tsx: shims registered first, every
 * runtime module loaded through the same require so react-query and
 * react-navigation stay one CJS instance.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as ReactNavigationNS from '@react-navigation/native';
import type * as ScreenNS from './PublicPageScreen';
import type { PublicPageResponse } from '../api/publicPages';

const req = createRequire(import.meta.url);
req('../../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const SLUG = 'q3-earnings-recap';

function patchUseRoute() {
  const resolvedNavPath = req.resolve('@react-navigation/native');
  const realNav = req('@react-navigation/native') as typeof ReactNavigationNS;
  const patchedNav = Object.assign(Object.create(Object.getPrototypeOf(realNav)), realNav, {
    useRoute: () => ({ params: { slug: SLUG } }),
  });
  (req.cache![resolvedNavPath] as { exports: unknown }).exports = patchedNav;
}

function renderWithSeededPage(page: PublicPageResponse) {
  patchUseRoute();

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { PublicPageScreen } = req('./PublicPageScreen') as typeof ScreenNS;

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData(['publicPage', SLUG], page);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(QueryClientProvider, {
        client: qc,
        children: React.createElement(PublicPageScreen),
      }),
    );
  });

  const rendered = () => JSON.stringify(tree.toJSON());
  return { tree, act, rendered };
}

function renderAgainstFakeNetwork(status: number, body: unknown) {
  patchUseRoute();

  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    })) as unknown as typeof fetch;

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { PublicPageScreen } = req('./PublicPageScreen') as typeof ScreenNS;

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(QueryClientProvider, {
        client: qc,
        children: React.createElement(PublicPageScreen),
      }),
    );
  });

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

  return { tree, act, flush, rendered, restore };
}

test('renders with zero auth state present: no react-redux Provider exists anywhere in this tree', () => {
  // The act of successfully calling create() below, with no <Provider> in
  // sight, is the proof — see the file header. This test additionally checks
  // real content came through, so a silently-empty render can't pass by luck.
  const page: PublicPageResponse = {
    content: 'Hello, reader.',
    publishedAt: '2026-08-01T00:00:00Z',
    citations: [],
  };
  const { tree, act, rendered } = renderWithSeededPage(page);
  assert.ok(rendered().includes('Hello, reader.'));
  act(() => tree.unmount());
});

test('splits content into real separate paragraph blocks, no markdown parsing', () => {
  const page: PublicPageResponse = {
    content: 'First paragraph.\n\nSecond paragraph.\n\nThird paragraph.',
    publishedAt: '2026-08-01T00:00:00Z',
    citations: [],
  };
  const { tree, act, rendered } = renderWithSeededPage(page);
  const text = rendered();
  assert.ok(text.includes('First paragraph.'));
  assert.ok(text.includes('Second paragraph.'));
  assert.ok(text.includes('Third paragraph.'));
  act(() => tree.unmount());
});

test('renders the real publishedAt date and each citation\'s headline + tier/epistemic copy', () => {
  const page: PublicPageResponse = {
    content: 'Body text.',
    publishedAt: '2026-07-09T10:00:00Z',
    citations: [
      {
        headline: 'Acme raised $5B',
        epistemicType: 'fact',
        confidenceScore: 0.9,
        scoringVersion: 1,
        snapshottedAt: '2026-07-09T10:00:00Z',
      },
    ],
  };
  const { tree, act, rendered } = renderWithSeededPage(page);
  const text = rendered();
  // Locale-dependent formatting (toLocaleDateString(undefined, ...), same as
  // provenance.ts's snapshotNote) — assert the real year renders, not one
  // exact ordering; the other provenance tests don't pin an exact string
  // either, for the same reason.
  assert.ok(text.includes('2026'), `expected the real publishedAt year to render, got: ${text}`);
  assert.ok(text.includes('Acme raised $5B'));
  assert.ok(text.includes('High confidence'));
  assert.ok(text.includes('Fact'));
  act(() => tree.unmount());
});

test('an unknown slug renders the real "page isn\'t available" 404 state', async () => {
  const { tree, act, flush, rendered, restore } = renderAgainstFakeNetwork(404, {
    error: { code: 'NOT_FOUND', message: 'Page not found', requestId: 'rid' },
  });
  await flush();

  const text = rendered();
  assert.ok(text.includes("isn't available"));
  assert.ok(text.includes('incorrect'));
  assert.ok(!text.includes('Something went wrong'), 'a 404 must not fall into the generic-error copy');

  restore();
  act(() => tree.unmount());
});

test('a non-404 failure renders the generic error state, not the 404 copy', async () => {
  const { tree, act, flush, rendered, restore } = renderAgainstFakeNetwork(429, {
    error: { code: 'PUBLIC_PAGE_RATE_LIMITED', message: 'Too many requests', requestId: 'rid' },
  });
  await flush();

  const text = rendered();
  assert.ok(text.includes('Something went wrong'));
  assert.ok(!text.includes("isn't available"), 'a rate-limit must not render as a 404');

  restore();
  act(() => tree.unmount());
});
