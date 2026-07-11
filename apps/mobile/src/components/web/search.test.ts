/**
 * Web command-bar search — the pure filter behind the ⌘K overlay.
 *
 * Scope is honest by design: connected sources + recent ingested items only
 * (claims/drafts/markets search is future scope and NOT covered here because
 * it is not built). These tests pin the matching, the blank-query behavior,
 * and the per-group cap.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { IntakeSource, RecentIntakeItem } from '@oryx/shared-types';
import { SEARCH_GROUP_CAP, searchWorkspace } from './search';

const source = (over: Partial<IntakeSource>): IntakeSource => ({
  id: 's-1',
  workspaceId: 'ws-1',
  kind: 'rss',
  name: 'Reuters Markets',
  enabled: true,
  config: {},
  health: 'healthy',
  lastSyncedAt: null,
  consecutiveFailures: 0,
  originKind: 'custom',
  originCatalogKey: null,
  originCustomId: null,
  ...over,
});

const item = (over: Partial<RecentIntakeItem>): RecentIntakeItem => ({
  id: 'i-1',
  subject: 'Fed holds rates steady',
  sourceName: 'Reuters Markets',
  providerName: 'rss',
  receivedAt: '2026-07-11T14:30:00Z',
  ...over,
});

test('matches sources by name and items by subject, case-insensitively', () => {
  const results = searchWorkspace(
    'reuters',
    [source({}), source({ id: 's-2', name: 'Bloomberg' })],
    [item({}), item({ id: 'i-2', subject: 'ECB cuts', sourceName: 'FT' })],
  );
  assert.deepEqual(results.sources.map((s) => s.id), ['s-1']);
  // 'reuters' also matches i-1 via its sourceName — real cross-field matching.
  assert.deepEqual(results.items.map((i) => i.id), ['i-1']);
});

test('matches item headlines with mixed-case queries', () => {
  const results = searchWorkspace('FED HOLDS', [], [item({})]);
  assert.deepEqual(results.items.map((i) => i.id), ['i-1']);
});

test('a blank or whitespace query returns nothing — the overlay shows its scope hint instead', () => {
  const results = searchWorkspace('   ', [source({})], [item({})]);
  assert.deepEqual(results, { sources: [], items: [] });
});

test('un-normalized items (null subject) never crash and still match on source name', () => {
  const results = searchWorkspace('reuters', [], [item({ subject: null })]);
  assert.deepEqual(results.items.map((i) => i.id), ['i-1']);
});

test('each group is capped so the palette stays a palette, not a page', () => {
  const manySources = Array.from({ length: 20 }, (_v, n) =>
    source({ id: `s-${n}`, name: `Feed ${n}` }),
  );
  const manyItems = Array.from({ length: 20 }, (_v, n) =>
    item({ id: `i-${n}`, subject: `Feed story ${n}` }),
  );
  const results = searchWorkspace('feed', manySources, manyItems);
  assert.equal(results.sources.length, SEARCH_GROUP_CAP);
  assert.equal(results.items.length, SEARCH_GROUP_CAP);
});

test('no match on either group returns empty groups (the overlay renders an honest empty state)', () => {
  const results = searchWorkspace('zzz-nothing', [source({})], [item({})]);
  assert.deepEqual(results, { sources: [], items: [] });
});
