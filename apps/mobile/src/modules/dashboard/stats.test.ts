/**
 * Command Center presenters — stats card + "Today" panel.
 *
 * SOURCES was a hardcoded "0" from Phase 1 until 2026-07-11; VERIFIED and
 * DRAFTS followed on 2026-07-11 (wired to /me verification.verifiedCount and
 * content.draftCount), and "Today" now presents the real recent-ingest feed
 * (GET /v1/intake/items/recent) instead of a permanent empty state. These
 * tests pin the presenters' whole contract; the backend halves are
 * test_intake_status_api.py, test_me_verified_count.py and
 * test_intake_recent_items.py.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import type { IntakeStatusSummary, RecentIntakeItem } from '@oryx/shared-types';
import { intakeItemIdOf } from '../activity/activityDetail';
import {
  TODAY_MAX_ROWS,
  draftsStatValue,
  providerTag,
  sourcesStatValue,
  todayCountSub,
  todayPanelState,
  todayRowTarget,
  verifiedStatValue,
} from './stats';

const seeded: IntakeStatusSummary = {
  total: 3,
  byHealth: { healthy: 2, degraded: 1, auth_required: 0, disabled: 0 },
};

test('Command Center SOURCES stat shows the real seeded source count, not zero', () => {
  assert.equal(sourcesStatValue(seeded), '3');
});

test('SOURCES stat shows an em dash while loading — never a fake zero', () => {
  assert.equal(sourcesStatValue(undefined), '—');
});

test('a genuine zero still renders as 0, not the loading dash', () => {
  assert.equal(
    sourcesStatValue({ total: 0, byHealth: { healthy: 0, degraded: 0, auth_required: 0, disabled: 0 } }),
    '0',
  );
});

// ---- VERIFIED + DRAFTS (from /me) -----------------------------------------

const seededMe = {
  verification: { pendingReviewCount: 4, openConflictCount: 1, verifiedCount: 306 },
  content: { draftCount: 5, pendingReviewCount: 1, scheduledCount: 1, publishedThisWeek: 2 },
};

test('VERIFIED stat shows verifiedCount from /me — verified + analyst_approved objects, not a hardcoded zero', () => {
  assert.equal(verifiedStatValue(seededMe), '306');
});

test('DRAFTS stat shows content.draftCount from /me, not a hardcoded zero', () => {
  assert.equal(draftsStatValue(seededMe), '5');
});

test('VERIFIED and DRAFTS show the em dash while /me is loading, and real zeros once loaded', () => {
  assert.equal(verifiedStatValue(undefined), '—');
  assert.equal(draftsStatValue(undefined), '—');
  const emptyMe = {
    verification: { pendingReviewCount: 0, openConflictCount: 0, verifiedCount: 0 },
    content: { draftCount: 0, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  };
  assert.equal(verifiedStatValue(emptyMe), '0');
  assert.equal(draftsStatValue(emptyMe), '0');
});

// ---- "Today" panel ---------------------------------------------------------

function item(overrides: Partial<RecentIntakeItem> & { id: string }): RecentIntakeItem {
  return {
    subject: 'A headline',
    sourceName: 'Yahoo Finance',
    providerName: 'rss',
    receivedAt: '2026-07-11T15:33:00+00:00',
    ...overrides,
  };
}

test('Today panel: while the feed query is loading it is NOT the empty state (no "connect a source" flash)', () => {
  assert.deepEqual(todayPanelState(undefined), { kind: 'loading' });
});

test('Today panel: a loaded-but-empty feed shows the connect-a-source empty state', () => {
  assert.deepEqual(todayPanelState([]), { kind: 'empty' });
});

test('Today panel: real items render headline + source in server order (newest first)', () => {
  const state = todayPanelState([
    item({ id: 'a', subject: 'Denim giant sees one trend surge 70%' }),
    item({ id: 'b', subject: 'Home Depot rolls out new rewards', sourceName: 'Reuters' }),
  ]);
  assert.equal(state.kind, 'list');
  assert.deepEqual(
    state.kind === 'list' ? state.rows.map((r) => [r.id, r.headline, r.source]) : [],
    [
      ['a', 'Denim giant sees one trend surge 70%', 'Yahoo Finance'],
      ['b', 'Home Depot rolls out new rewards', 'Reuters'],
    ],
  );
});

test('Today panel: caps at TODAY_MAX_ROWS so the brief never becomes a feed', () => {
  const many = Array.from({ length: TODAY_MAX_ROWS + 4 }, (_, i) => item({ id: `i${i}` }));
  const state = todayPanelState(many);
  assert.equal(state.kind === 'list' ? state.rows.length : -1, TODAY_MAX_ROWS);
});

test('Today panel: a not-yet-normalized item (null/blank subject) never renders a blank headline', () => {
  const state = todayPanelState([
    item({ id: 'n1', subject: null }),
    item({ id: 'n2', subject: '   ' }),
  ]);
  assert.deepEqual(
    state.kind === 'list' ? state.rows.map((r) => r.headline) : [],
    ['Untitled item', 'Untitled item'],
  );
});

// ---- CC-3 row anatomy: provider tag chip + header count sub ----------------

test('providerTag maps all five real intake providers and uppercases unknown ones', () => {
  // The full backend IntakeProviderName literal (shared/types.py:567).
  assert.equal(providerTag('gmail'), 'GMAIL');
  assert.equal(providerTag('rss'), 'RSS');
  assert.equal(providerTag('webhook'), 'WEBHOOK');
  assert.equal(providerTag('api_pull'), 'API');
  assert.equal(providerTag('manual'), 'MANUAL');
  // TS types providerName as string — an unknown value must never get a
  // wrong known label, just its own uppercase.
  assert.equal(providerTag('carrier_pigeon'), 'CARRIER_PIGEON');
});

test('every Today row carries the provider tag for its leading chip', () => {
  const state = todayPanelState([
    item({ id: 'a', providerName: 'rss' }),
    item({ id: 'b', providerName: 'gmail' }),
    item({ id: 'c', providerName: 'api_pull' }),
  ]);
  assert.deepEqual(
    state.kind === 'list' ? state.rows.map((r) => r.tag) : [],
    ['RSS', 'GMAIL', 'API'],
  );
});

test('todayCountSub states the real rendered row count and stays silent while loading', () => {
  assert.equal(todayCountSub({ kind: 'loading' }), undefined);
  assert.equal(todayCountSub({ kind: 'empty' }), '0 ITEMS');
  const one = todayPanelState([item({ id: 'a' })]);
  assert.equal(todayCountSub(one), '1 ITEM');
  const six = todayPanelState(
    Array.from({ length: TODAY_MAX_ROWS + 4 }, (_, i) => item({ id: `i${i}` })),
  );
  // The sub is the RENDERED count (capped), never the uncapped feed length.
  assert.equal(todayCountSub(six), `${TODAY_MAX_ROWS} ITEMS`);
});

// ---- Today-row press → IntakeItemDetail (2026-07-12) -----------------------

test('pressing a Today headline targets IntakeItemDetail with that row\'s real intake item id', () => {
  // Full flow: the /items/recent shape → panel row → press target. The id the
  // press carries is the SAME id the backend returned for the ingested item,
  // so the detail screen fetches the full real content (headline, body,
  // source/sender/received, links) — never a blank or partial view.
  const state = todayPanelState([
    item({ id: '8d966016-8d27-4df5-bb1f-ea999919294e', subject: 'Fed holds rates steady' }),
  ]);
  assert.equal(state.kind, 'list');
  const row = state.kind === 'list' ? state.rows[0]! : (undefined as never);
  assert.deepEqual(todayRowTarget(row), {
    screen: 'IntakeItemDetail',
    params: { itemId: '8d966016-8d27-4df5-bb1f-ea999919294e' },
  });
});

test('a Today press and an Activity press on the same ingested item resolve to the IDENTICAL destination', () => {
  // Same screen, not a thinner duplicate: build both paths' targets for one
  // item. Activity resolves the id from the event payload (intakeItemIdOf) and
  // navigates to the literal IntakeItemDetail route; Today resolves it from
  // the /items/recent row. Both must be deep-equal — and SettingsStack
  // registers exactly one component (ItemDetailScreen) for that route name,
  // so equal targets means the same real screen. The params type of
  // todayRowTarget is SettingsStackParamList['IntakeItemDetail'], so drifting
  // from the registered route's shape fails type-check as well.
  const itemId = 'b2f1c000-0000-4000-8000-00000000cafe';
  const viaActivity = {
    screen: 'IntakeItemDetail',
    params: { itemId: intakeItemIdOf({ data: { intakeItemId: itemId } })! },
  };
  const viaToday = todayRowTarget({ id: itemId });
  assert.deepEqual(viaToday, viaActivity);
});

test('the stale "PHASE 1 — FOUNDATION" badge is gone from Command Center source', () => {
  // The repo has no component-render harness (pure-logic tests only), so the
  // honest available proof is source-level: the screen file no longer contains
  // the badge string or the __DEV__ block that rendered it.
  const source = readFileSync(
    fileURLToPath(new URL('./screens/DashboardScreen.tsx', import.meta.url)),
    'utf8',
  );
  assert.ok(!source.includes('PHASE 1'), 'badge text must be removed');
  assert.ok(!source.includes('FOUNDATION'), 'badge text must be removed');
  assert.ok(!source.includes('__DEV__'), 'the badge\'s __DEV__ block must be gone entirely');
});
