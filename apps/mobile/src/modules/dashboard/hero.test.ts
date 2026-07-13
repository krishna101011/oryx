/**
 * Command Center hero (CC-1/CC-2 wave, 2026-07-12) — the date/time kicker,
 * the honest summary sentence, and the source-scan proofs that the KPI tiles
 * and Today rows follow the decided anatomy (no component-render harness
 * exists; source scanning is the established honest proof, see
 * stats.test.ts's badge test).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { heroKicker, heroSummary } from './hero';

/** Comments stripped: the scans assert what the screen RENDERS, and the
 * screen's own comments legitimately name the things it must not render. */
const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const screenSource = (): string =>
  stripComments(
    readFileSync(
      fileURLToPath(new URL('./screens/DashboardScreen.tsx', import.meta.url)),
      'utf8',
    ),
  );

// ---- heroKicker -------------------------------------------------------------

test('heroKicker renders a real Date as WEEKDAY · MON DD · HH:MM, zero-padded', () => {
  // 2026-01-02 is a Friday (2026-01-01 is a Thursday).
  assert.equal(heroKicker(new Date(2026, 0, 2, 9, 5)), 'FRIDAY · JAN 02 · 09:05');
  assert.equal(heroKicker(new Date(2026, 11, 31, 23, 59)), 'THURSDAY · DEC 31 · 23:59');
});

// ---- heroSummary ------------------------------------------------------------

const loadedStatus = { total: 19 };
const loadedMe = {
  verification: { pendingReviewCount: 4, openConflictCount: 1, verifiedCount: 306 },
  content: { draftCount: 2, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
};

const sentence = (segs: { text: string }[]): string => segs.map((s) => s.text).join('');

test('heroSummary builds the sentence from the three confirmed real fields only', () => {
  assert.equal(
    sentence(heroSummary(loadedStatus, loadedMe)),
    '19 sources connected, 4 claims awaiting review, and 2 drafts in progress.',
  );
});

test('heroSummary never fabricates a number — unresolved queries render an em dash, not 0', () => {
  assert.equal(
    sentence(heroSummary(undefined, undefined)),
    '— sources connected, — claims awaiting review, and — drafts in progress.',
  );
  // Mixed: one query resolved, the other still loading.
  assert.equal(
    sentence(heroSummary(loadedStatus, undefined)),
    '19 sources connected, — claims awaiting review, and — drafts in progress.',
  );
});

test('heroSummary states real zeros plainly — the sentence is never omitted to hide an empty state', () => {
  const emptyMe = {
    verification: { pendingReviewCount: 0, openConflictCount: 0, verifiedCount: 0 },
    content: { draftCount: 0, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  };
  assert.equal(
    sentence(heroSummary({ total: 0 }, emptyMe)),
    '0 sources connected, 0 claims awaiting review, and 0 drafts in progress.',
  );
});

test('heroSummary uses singular words for exactly one of anything', () => {
  const oneMe = {
    verification: { pendingReviewCount: 1, openConflictCount: 0, verifiedCount: 1 },
    content: { draftCount: 1, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  };
  assert.equal(
    sentence(heroSummary({ total: 1 }, oneMe)),
    '1 source connected, 1 claim awaiting review, and 1 draft in progress.',
  );
});

test('the real numbers are the strong segments — nothing else is highlighted', () => {
  const segs = heroSummary(loadedStatus, loadedMe);
  assert.deepEqual(
    segs.filter((s) => s.strong).map((s) => s.text),
    ['19', '4', '2'],
  );
});

// ---- Source-scan proofs (CC-2 tiles, CC-3/CC-4 rows) ------------------------

test('KPI tiles render kpiVal and never invent a sparkline, delta, or sentiment chip', () => {
  const source = screenSource();
  assert.ok(source.includes('variant="kpiVal"'), 'tile values must be kpiVal');
  // No real time series exists for Sources/Verified/Drafts (rollups measure
  // pipeline events, not these stock counts) — so no Spark may be imported,
  // and no delta/trend/sentiment may render.
  assert.ok(!/\bSpark\b/.test(source), 'no sparkline without a real series');
  assert.ok(!source.includes('delta'), 'no delta without prior-period data');
  assert.ok(!source.includes('trend'), 'no trend without prior-period data');
  assert.ok(!/RISK-ON|RISK-OFF|sentiment/i.test(source), 'no sentiment chip — nothing real backs it');
});

test('the Today card is wired through CardHeader + HairlineRowList with a leading tag chip', () => {
  const source = screenSource();
  assert.ok(source.includes('<CardHeader title="Today"'), 'real CardHeader in the header slot');
  assert.ok(source.includes('todayCountSub'), 'header sub is the real item count');
  assert.ok(source.includes('<HairlineRowList>'), 'rows pack through HairlineRowList');
  assert.ok(
    source.includes('gx.chip') && source.includes('gx.chipIndigo'),
    'each row leads with the reference tag chip (command-center.jsx:84 anatomy)',
  );
  assert.ok(source.includes('{row.tag}'), 'the chip text is the real provider tag');
});

test('the hero kicker and wash are real: heroKicker(new Date()) and token-only HeroWash', () => {
  const source = screenSource();
  assert.ok(source.includes('heroKicker(new Date())'), 'kicker uses the real clock');
  assert.ok(source.includes('<HeroWash />'), 'radial wash present');
  const wash = stripComments(
    readFileSync(
      fileURLToPath(new URL('./components/HeroWash.tsx', import.meta.url)),
      'utf8',
    ),
  );
  assert.ok(
    wash.includes('t.colors.accent.plum') && wash.includes('t.colors.accent.teal'),
    'wash stops come from existing tokens only',
  );
  assert.ok(!/#[0-9a-fA-F]{6}/.test(wash), 'no hardcoded hex in the wash');
});
