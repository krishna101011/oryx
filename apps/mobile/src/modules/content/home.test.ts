/**
 * Content Studio design-foundation wave (CS-1/CS-2, 2026-07-15) — toolbar
 * action registry, draft row presenters, and a token-violation scan. Source
 * scans follow the established pattern (no component-render harness).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  CONTENT_ACTIONS,
  draftCountSub,
  draftMeta,
  draftStatusChip,
  draftUpdatedDate,
} from './home';

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const read = (rel: string): string =>
  stripComments(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8'));

// ---- CS-1: toolbar action parity --------------------------------------------

test('CONTENT_ACTIONS preserves every action the old five stacked buttons carried, none dropped', () => {
  const screens = CONTENT_ACTIONS.map((a) => a.screen);
  assert.deepEqual(screens, [
    'GenerateDraft',
    'ReviewQueue',
    'PublishTargets',
    'PublishHistory',
    'Calendar',
  ]);
  // Exactly one primary action (the generate CTA) — the other four are equal-weight.
  assert.equal(CONTENT_ACTIONS.filter((a) => a.primary).length, 1);
  assert.equal(CONTENT_ACTIONS.find((a) => a.primary)?.screen, 'GenerateDraft');
});

test('the toolbar renders one pressable per CONTENT_ACTIONS entry, navigating by its real screen name', () => {
  const screen = read('./screens/ContentHomeScreen.tsx');
  assert.ok(screen.includes('CONTENT_ACTIONS.map'), 'toolbar maps the real action registry');
  assert.ok(screen.includes('navigateTo(action.screen)'), 'navigates by the action entry, not a hardcoded literal');
});

// ---- CS-2: draft row presenters ----------------------------------------------

test('draftStatusChip is exhaustive on the real DraftStatus union and follows the reference tone families', () => {
  assert.deepEqual(draftStatusChip('approved'), { label: 'APPROVED', tone: 'positive' });
  assert.deepEqual(draftStatusChip('scheduled'), { label: 'SCHEDULED', tone: 'positive' });
  assert.deepEqual(draftStatusChip('published'), { label: 'PUBLISHED', tone: 'positive' });
  assert.deepEqual(draftStatusChip('in_review'), { label: 'IN REVIEW', tone: 'warn' });
  assert.deepEqual(draftStatusChip('changes_requested'), {
    label: 'CHANGES REQUESTED',
    tone: 'warn',
  });
  assert.deepEqual(draftStatusChip('rejected'), { label: 'REJECTED', tone: 'negative' });
  assert.deepEqual(draftStatusChip('draft'), { label: 'DRAFT', tone: 'neutral' });
  assert.deepEqual(draftStatusChip('archived'), { label: 'ARCHIVED', tone: 'neutral' });
});

test('draftUpdatedDate renders only the real updatedAt, nothing for an unparseable timestamp', () => {
  assert.equal(draftUpdatedDate({ updatedAt: '2026-07-13T09:15:00Z' }), '2026-07-13');
  assert.equal(draftUpdatedDate({ updatedAt: 'not-a-date' }), undefined);
});

test('draftMeta builds the mono meta line from real fields only — format, word count when present, version', () => {
  assert.equal(
    draftMeta({ format: 'article', wordCount: 312, currentVersion: 3 }),
    'ARTICLE · 312 WORDS · v3',
  );
  assert.equal(
    draftMeta({ format: 'tweet_thread', wordCount: null, currentVersion: 1 }),
    'TWEET · v1',
  );
});

test('draftCountSub stays silent while loading, states a real zero plainly, and pluralizes', () => {
  assert.equal(draftCountSub(undefined), undefined);
  assert.equal(draftCountSub([]), '0 DRAFTS');
});

test('DraftCard renders only real ContentDraft fields — no channel list is invented', () => {
  const row = read('./components/DraftCard.tsx');
  assert.ok(row.includes('draftStatusChip'), 'status chip from the real status');
  assert.ok(row.includes('draftUpdatedDate'), 'mono date column from the real updatedAt');
  assert.ok(row.includes('draftMeta'), 'mono meta line from real format/wordCount/version');
  // No invented per-draft channel data — the honest RW-1-style disclosure.
  assert.ok(!/channel|\bch\b\s*[:.]/i.test(row), 'no invented channel list');
});

test('the content screen and draft row wire through Card/CardHeader/HairlineRowList like every other rebuilt list', () => {
  const screen = read('./screens/ContentHomeScreen.tsx');
  assert.ok(screen.includes('<CardHeader title="Actions"'), 'toolbar sits in a real card-head');
  assert.ok(screen.includes('<CardHeader title="Drafts"'), 'drafts card has a real header');
  assert.ok(screen.includes('draftCountSub(drafts.data)'), 'header sub is the real count');
  assert.ok(screen.includes('<HairlineRowList>'), 'draft rows pack through HairlineRowList');
});

// ---- no hardcoded color introduced -------------------------------------------

test('no hardcoded hex or rgba color is introduced in the touched CS-1/CS-2 files', () => {
  for (const rel of ['./screens/ContentHomeScreen.tsx', './components/DraftCard.tsx', './home.ts']) {
    const source = read(rel);
    assert.ok(!/rgba?\(/.test(source), `${rel}: no rgba()/rgb() literals`);
    assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(source), `${rel}: no hex literals`);
  }
});
