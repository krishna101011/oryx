/**
 * Rendered-press regression proving the source-catalog picker rebuild wires
 * through the REAL origin_kind='catalog' intake_sources path (POST to
 * create, PATCH to flip `enabled`) and never the old WorkspaceSource toggle
 * (PUT /sources/workspace/{key}) — recon confirmed that path has zero real
 * pipeline effect. Same harness rules as research/rowNavigation.test.tsx:
 * register the platform shims BEFORE anything importing react-native, and
 * load every runtime module through the same require function so
 * react-query stays one CJS instance.
 *
 * global.fetch is monkey-patched to a tiny in-memory fake backend (no real
 * network) so the mutations' real onSuccess -> invalidateQueries ->
 * automatic refetch chain has something to resolve against; the test then
 * asserts on the exact HTTP calls that fake backend recorded.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as ReactQueryNS from '@tanstack/react-query';
import type * as DesignSystemNS from '@oryx/design-system';
import type * as ClientNS from '../../lib/api/client';
import type * as TrustedScreenNS from '../settings/screens/TrustedSourcesScreen';
import type { IntakeSource, SourceCatalogEntry } from '@oryx/shared-types';

const req = createRequire(import.meta.url);
req('../../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

const CATALOG: SourceCatalogEntry[] = [
  { key: 'coindesk', name: 'CoinDesk', url: 'https://www.coindesk.com/arc/outboundfeeds/rss/', focus: 'crypto', editorialConfidence: 78 },
  { key: 'cointelegraph', name: 'Cointelegraph', url: 'https://cointelegraph.com/rss', focus: 'crypto', editorialConfidence: 76 },
  { key: 'decrypt', name: 'Decrypt', url: 'https://decrypt.co/feed', focus: 'crypto', editorialConfidence: 75 },
  { key: 'the_block', name: 'The Block', url: 'https://www.theblock.co/rss.xml', focus: 'crypto', editorialConfidence: 82 },
  { key: 'yahoo_finance', name: 'Yahoo Finance', url: 'https://finance.yahoo.com/news/rssindex', focus: 'markets', editorialConfidence: 80 },
  { key: 'investing_company_news', name: 'Investing.com Company News', url: 'https://www.investing.com/rss/news_356.rss', focus: 'markets', editorialConfidence: 78 },
  { key: 'investing_earnings', name: 'Investing.com Earnings Reports & Whispers', url: 'https://www.investing.com/rss/news_1063.rss', focus: 'markets', editorialConfidence: 76 },
  { key: 'investing_stock_market_news', name: 'Investing.com Stock Market News', url: 'https://www.investing.com/rss/news_25.rss', focus: 'markets', editorialConfidence: 80 },
];

interface FakeCall {
  method: string;
  path: string;
  body: Record<string, unknown> | undefined;
}

/** A tiny in-memory fake backend: tracks real intake_sources state, records
 * every call it received, and would throw on any /sources/workspace hit —
 * proving the old path is never touched. */
function makeFakeBackend(initialSources: IntakeSource[] = []) {
  let sources = [...initialSources];
  const calls: FakeCall[] = [];
  let nextId = 1;

  const json = (data: unknown, status = 200): Response =>
    new Response(JSON.stringify({ data }), {
      status,
      headers: { 'content-type': 'application/json' },
    });

  const fetchImpl = async (input: unknown, init?: RequestInit): Promise<Response> => {
    const full = String(input);
    const path = full.replace(/^https?:\/\/[^/]+\/v1/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body =
      init?.body !== undefined
        ? (JSON.parse(String(init.body)) as Record<string, unknown>)
        : undefined;
    calls.push({ method, path, body });

    if (path.startsWith('/sources/workspace')) {
      throw new Error(`FORBIDDEN in this flow: ${method} ${path} (dead WorkspaceSource path)`);
    }
    if (method === 'GET' && path === '/sources/catalog') {
      return json(CATALOG);
    }
    if (method === 'GET' && path === '/intake/sources') {
      return json(sources);
    }
    if (method === 'GET' && path === '/intake/status') {
      return json({
        total: sources.length,
        byHealth: { healthy: sources.length, degraded: 0, auth_required: 0, disabled: 0 },
      });
    }
    if (method === 'POST' && path === '/intake/sources') {
      const catalogKey = body?.origin_catalog_key as string;
      const entry = CATALOG.find((e) => e.key === catalogKey);
      const created: IntakeSource = {
        id: `new-${nextId++}`,
        workspaceId: 'ws-1',
        kind: 'rss',
        name: entry?.name ?? 'unknown',
        enabled: true,
        config: { feed_url: entry?.url ?? '' },
        health: 'healthy',
        lastSyncedAt: null,
        consecutiveFailures: 0,
        originKind: 'catalog',
        originCatalogKey: catalogKey,
        originCustomId: null,
      };
      sources = [...sources, created];
      return json(created);
    }
    const patchMatch = /^\/intake\/sources\/([^/?]+)$/.exec(path);
    if (method === 'PATCH' && patchMatch) {
      const id = patchMatch[1];
      sources = sources.map((s) => (s.id === id ? { ...s, enabled: body?.enabled as boolean } : s));
      return json(sources.find((s) => s.id === id));
    }
    throw new Error(`unhandled fake fetch: ${method} ${path}`);
  };

  return { fetchImpl, calls, getSources: () => sources };
}

function renderTrustedSources(initialSources: IntakeSource[] = []) {
  const backend = makeFakeBackend(initialSources);
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = backend.fetchImpl as unknown as typeof fetch;

  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { TrustedSourcesScreen } = req(
    '../settings/screens/TrustedSourcesScreen',
  ) as typeof TrustedScreenNS;

  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  qc.setQueryData(['sources', 'catalog'], CATALOG);
  qc.setQueryData(['intake', 'sources'], initialSources);

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(TrustedSourcesScreen),
      ),
    );
  });

  const pressByLabel = (label: string) => {
    const matches = tree.root.findAll(
      (node) =>
        (node.type as unknown) === 'Pressable' &&
        node.props.accessibilityLabel === label &&
        typeof node.props.onPress === 'function',
    );
    assert.equal(matches.length, 1, `exactly one pressable labeled "${label}"`);
    act(() => {
      matches[0]!.props.onPress();
    });
  };

  const flush = async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  };

  const rendered = () => JSON.stringify(tree.toJSON());

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, act, pressByLabel, flush, rendered, backend, restore };
}

/**
 * Same real TrustedSourcesScreen, but the catalog query is deliberately left
 * unresolved (a fetch that never settles) so `useSourceCatalog().isLoading`
 * stays true for the assertion — proving the real screen actually passes
 * `isLoading` through to CatalogSourcePicker, not just that the component
 * supports the prop in isolation (see CatalogSourcePicker.test.tsx for that).
 */
function renderTrustedSourcesLoading() {
  const originalFetch = globalThis.fetch;
  (globalThis as unknown as { fetch: typeof fetch }).fetch = (() =>
    new Promise<Response>(() => {})) as unknown as typeof fetch;

  const { configureApiClient } = req('../../lib/api/client') as typeof ClientNS;
  configureApiClient({
    baseUrl: 'http://test.local/v1',
    getAccessToken: () => 'test-token',
    getWorkspaceId: () => 'ws-1',
    refreshAccessToken: async () => null,
  });

  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { QueryClient, QueryClientProvider } = req(
    '@tanstack/react-query',
  ) as typeof ReactQueryNS;
  const { TrustedSourcesScreen } = req(
    '../settings/screens/TrustedSourcesScreen',
  ) as typeof TrustedScreenNS;

  // No qc.setQueryData(['sources', 'catalog'], ...) — deliberately unseeded.
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(TrustedSourcesScreen),
      ),
    );
  });

  const restore = () => {
    (globalThis as unknown as { fetch: typeof fetch }).fetch = originalFetch;
  };

  return { tree, rendered: () => JSON.stringify(tree.toJSON()), restore };
}

test('renders both real sections (Crypto, Markets) with real names, including The Block', () => {
  const { tree, rendered, restore } = renderTrustedSources([]);
  const text = rendered();
  assert.ok(text.includes('CRYPTO'), 'Crypto section header renders');
  assert.ok(text.includes('MARKETS'), 'Markets section header renders');
  for (const name of [
    'CoinDesk',
    'Cointelegraph',
    'Decrypt',
    'The Block',
    'Yahoo Finance',
    'Investing.com Company News',
    'Investing.com Earnings Reports & Whispers',
    'Investing.com Stock Market News',
  ]) {
    assert.ok(text.includes(name), `${name} renders as a real tile`);
  }
  tree.unmount();
  restore();
});

test('pressing an unactivated tile calls the REAL POST /intake/sources catalog-activation endpoint, never /sources/workspace', async () => {
  const { tree, pressByLabel, flush, rendered, backend, restore } = renderTrustedSources([]);

  assert.ok(
    rendered().includes('Editorial confidence: 78') && rendered().includes('Investing.com Company News'),
    'the tile starts unselected with its real confidence description',
  );

  pressByLabel('Investing.com Company News');
  await flush();

  const creates = backend.calls.filter((c) => c.method === 'POST' && c.path === '/intake/sources');
  assert.equal(creates.length, 1, 'exactly one real create call fired');
  assert.equal(creates[0]!.body?.origin_kind, 'catalog');
  assert.equal(creates[0]!.body?.origin_catalog_key, 'investing_company_news');

  assert.ok(
    backend.getSources().some((s) => s.originCatalogKey === 'investing_company_news' && s.enabled),
    'a real intake_sources row now exists for this catalog key',
  );
  assert.equal(
    backend.calls.filter((c) => c.path.startsWith('/sources/workspace')).length,
    0,
    'the dead WorkspaceSource toggle path was never called',
  );

  tree.unmount();
  restore();
});

test('pressing an already-activated tile calls the REAL PATCH endpoint to disable it, not a delete or a WorkspaceSource write', async () => {
  const existing: IntakeSource = {
    id: 'existing-1',
    workspaceId: 'ws-1',
    kind: 'rss',
    name: 'CoinDesk',
    enabled: true,
    config: { feed_url: 'https://www.coindesk.com/arc/outboundfeeds/rss/' },
    health: 'healthy',
    lastSyncedAt: null,
    consecutiveFailures: 0,
    originKind: 'catalog',
    originCatalogKey: 'coindesk',
    originCustomId: null,
  };
  const { tree, pressByLabel, flush, backend, restore } = renderTrustedSources([existing]);

  pressByLabel('CoinDesk');
  await flush();

  const patches = backend.calls.filter(
    (c) => c.method === 'PATCH' && c.path === '/intake/sources/existing-1',
  );
  assert.equal(patches.length, 1, 'exactly one real patch call fired');
  assert.equal(patches[0]!.body?.enabled, false);
  assert.equal(
    backend.calls.filter((c) => c.path.startsWith('/sources/workspace')).length,
    0,
    'the dead WorkspaceSource toggle path was never called',
  );

  tree.unmount();
  restore();
});

test('while the real catalog query is loading, TrustedSourcesScreen shows 3 shaped ChoiceTile skeletons, never a blank picker', () => {
  const { tree, rendered, restore } = renderTrustedSourcesLoading();
  const { Card } = req('@oryx/design-system') as typeof DesignSystemNS;

  assert.equal(
    tree.root.findAllByType(Card as never).length,
    3,
    'the real screen renders 3 bordered Cards — one per shaped ChoiceTile skeleton — while catalog.isLoading is true',
  );
  assert.ok(!rendered().includes('CRYPTO'), 'no section header renders yet');
  assert.ok(!rendered().includes('CoinDesk'), 'no tile renders yet');

  tree.unmount();
  restore();
});

test('regression: TrustedSourcesScreen and FocusAndSourcesScreen source no longer reference WorkspaceSource at all', () => {
  const read = (rel: string): string =>
    readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8');

  for (const rel of [
    '../settings/screens/TrustedSourcesScreen.tsx',
    '../onboarding/screens/FocusAndSourcesScreen.tsx',
  ]) {
    const source = read(rel);
    assert.ok(!source.includes('WorkspaceSource'), `${rel}: no WorkspaceSource type/import`);
    assert.ok(!source.includes('sources/workspace'), `${rel}: no /sources/workspace endpoint call`);
    assert.ok(!source.includes('UpdateWorkspaceSourceRequest'), `${rel}: no dead request type`);
  }
});
