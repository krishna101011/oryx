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
import { test } from 'node:test';
import type { IntakeStatusSummary, RecentIntakeItem } from '@oryx/shared-types';
import {
  TODAY_MAX_ROWS,
  draftsStatValue,
  sourcesStatValue,
  todayPanelState,
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
