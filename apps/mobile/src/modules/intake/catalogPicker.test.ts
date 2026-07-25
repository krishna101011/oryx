import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { IntakeSource, SourceCatalogEntry } from '@oryx/shared-types';
import {
  activatableCatalogEntries,
  buildCatalogActivationMap,
  filterCatalogByFocus,
  groupCatalogBySection,
  isCatalogKeyEnabled,
  keysMissingActivation,
  resolveToggleAction,
} from './catalogPicker';

/** The 8 real source_catalog rows as of migration 0028. */
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

function source(overrides: Partial<IntakeSource>): IntakeSource {
  return {
    id: 'src-1',
    workspaceId: 'ws-1',
    kind: 'rss',
    name: 'x',
    enabled: true,
    config: {},
    health: 'healthy',
    lastSyncedAt: null,
    consecutiveFailures: 0,
    originKind: 'catalog',
    originCatalogKey: 'coindesk',
    originCustomId: null,
    ...overrides,
  };
}

test('activatableCatalogEntries includes every catalog entry (the_block got its real feed in migration 0028)', () => {
  const entries = activatableCatalogEntries(CATALOG);
  assert.equal(entries.length, 8);
  assert.ok(entries.some((e) => e.key === 'the_block'));
});

test('groupCatalogBySection produces exactly 4 crypto + 4 markets', () => {
  const sections = groupCatalogBySection(CATALOG);
  assert.equal(sections.length, 2);
  const crypto = sections.find((s) => s.title === 'Crypto')!;
  const markets = sections.find((s) => s.title === 'Markets')!;
  assert.deepEqual(
    crypto.entries.map((e) => e.key).sort(),
    ['coindesk', 'cointelegraph', 'decrypt', 'the_block'],
  );
  assert.deepEqual(
    markets.entries.map((e) => e.key).sort(),
    ['investing_company_news', 'investing_earnings', 'investing_stock_market_news', 'yahoo_finance'],
  );
});

test('groupCatalogBySection omits a section entirely when it would be empty', () => {
  const onlyCrypto = CATALOG.filter((e) => e.focus === 'crypto');
  const sections = groupCatalogBySection(onlyCrypto);
  assert.equal(sections.length, 1);
  assert.equal(sections[0]!.title, 'Crypto');
});

test('filterCatalogByFocus: "both" returns everything, a specific focus narrows to that focus + "both"-tagged entries', () => {
  assert.equal(filterCatalogByFocus(CATALOG, 'both').length, CATALOG.length);
  const crypto = filterCatalogByFocus(CATALOG, 'crypto');
  assert.ok(crypto.every((e) => e.focus === 'crypto' || e.focus === 'both'));
  assert.ok(crypto.some((e) => e.key === 'coindesk'));
  assert.ok(!crypto.some((e) => e.key === 'yahoo_finance'));
});

test('buildCatalogActivationMap keys only real catalog-origin sources by their catalog key', () => {
  const sources = [
    source({ id: 's1', originKind: 'catalog', originCatalogKey: 'coindesk', enabled: true }),
    source({ id: 's2', originKind: 'custom', originCatalogKey: null, enabled: true }),
    source({ id: 's3', originKind: 'catalog', originCatalogKey: 'decrypt', enabled: false }),
  ];
  const map = buildCatalogActivationMap(sources);
  assert.deepEqual(Object.keys(map).sort(), ['coindesk', 'decrypt']);
  assert.equal(map.coindesk!.id, 's1');
  assert.equal(isCatalogKeyEnabled(map, 'coindesk'), true);
  assert.equal(isCatalogKeyEnabled(map, 'decrypt'), false);
  assert.equal(isCatalogKeyEnabled(map, 'the_block'), false);
});

test('resolveToggleAction: no existing row -> create; existing enabled row -> patch to disabled; existing disabled row -> patch to enabled', () => {
  const map = buildCatalogActivationMap([
    source({ id: 's1', originCatalogKey: 'coindesk', enabled: true }),
    source({ id: 's2', originCatalogKey: 'decrypt', enabled: false }),
  ]);

  assert.deepEqual(resolveToggleAction('cointelegraph', map), {
    kind: 'create',
    catalogKey: 'cointelegraph',
  });
  assert.deepEqual(resolveToggleAction('coindesk', map), {
    kind: 'patch',
    sourceId: 's1',
    enabled: false,
  });
  assert.deepEqual(resolveToggleAction('decrypt', map), {
    kind: 'patch',
    sourceId: 's2',
    enabled: true,
  });
});

test('keysMissingActivation lists activatable keys with no real row yet, including the_block', () => {
  const map = buildCatalogActivationMap([
    source({ id: 's1', originCatalogKey: 'coindesk', enabled: true }),
  ]);
  const missing = keysMissingActivation(CATALOG, map).sort();
  assert.deepEqual(missing, [
    'cointelegraph',
    'decrypt',
    'investing_company_news',
    'investing_earnings',
    'investing_stock_market_news',
    'the_block',
    'yahoo_finance',
  ]);
});

test('keysMissingActivation is empty once every activatable key has a real row', () => {
  const map = buildCatalogActivationMap(
    activatableCatalogEntries(CATALOG).map((e, i) =>
      source({ id: `s${i}`, originCatalogKey: e.key, enabled: true }),
    ),
  );
  assert.deepEqual(keysMissingActivation(CATALOG, map), []);
});
