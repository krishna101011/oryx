/**
 * Automation Hub KPI presenter tests (AH-1) + the wave's honesty scans:
 * every tile traces to a real source, the estimated "Saved analyst hours"
 * tile is absent, the read-only Rules tab gained no toggle, and no hardcoded
 * radius/color literals remain on the screen (source-scan precedent:
 * foundation.test.ts / stats.test.ts badge-removal).
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import type { AlertPreference, Automation } from '@oryx/shared-types';
import { FEED_PAGE_LIMIT, activeRulesValue, hubKpis, window24h } from './stats';

const NOW = new Date('2026-07-16T12:00:00Z');

const pref = (
  type: string,
  channel: string,
  frequency: AlertPreference['frequency'],
): AlertPreference =>
  ({ type, channel, frequency, quietHours: null }) as AlertPreference;

/** The complete resolved grid the API returns (4 categories × 3 channels). */
const grid = (offCategories: string[] = []): AlertPreference[] =>
  ['security', 'system', 'verification', 'publishing'].flatMap((c) =>
    ['in_app', 'push', 'email'].map((ch) =>
      pref(c, ch, offCategories.includes(c) && ch === 'in_app' ? 'off' : 'instant'),
    ),
  );

const entry = (
  action: Automation.AutomationAction,
  createdAt: string,
): Automation.AutomationLogEntry => ({
  id: `${action}-${createdAt}`,
  kind: action === 'digest_sent' ? 'digest' : 'dispatch',
  action,
  eventType: action === 'digest_sent' ? null : 'content.publish.failed',
  category: null,
  frequency: null,
  windowStart: null,
  windowEnd: null,
  activityInboxId: null,
  channel: action === 'digest_sent' ? null : 'in_app',
  detail: null,
  createdAt,
});

// ---- ACTIVE RULES — the resolved in-app cadence grid ------------------------

test('activeRulesValue counts categories whose in-app cadence is on, over the 4 real categories', () => {
  assert.equal(activeRulesValue(grid()), '4/4');
  assert.equal(activeRulesValue(grid(['security'])), '3/4');
  assert.equal(
    activeRulesValue(grid(['security', 'system', 'verification', 'publishing'])),
    '0/4',
  );
});

test('activeRulesValue ignores push/email rows — only the in_app channel decides', () => {
  const prefs = grid().map((p) =>
    p.channel === 'push' ? { ...p, frequency: 'off' as const } : p,
  );
  assert.equal(activeRulesValue(prefs), '4/4');
});

test('activeRulesValue shows an honest dash while loading, never a fabricated zero', () => {
  assert.equal(activeRulesValue(undefined), '—');
});

// ---- DECISIONS/FAILURES · 24H — the automation-log window -------------------

test('window24h counts only entries inside the last 24 hours', () => {
  const entries = [
    entry('notification_created', '2026-07-16T11:00:00Z'), // in
    entry('push_failed', '2026-07-16T00:00:00Z'), // in
    entry('digest_sent', '2026-07-15T11:59:00Z'), // out (24h01m ago)
    entry('email_failed', '2026-07-10T00:00:00Z'), // out
  ];
  const win = window24h(entries, NOW);
  assert.equal(win.decisions, 2);
  assert.equal(win.failures, 1);
  assert.equal(win.truncated, false);
});

test('window24h flags truncation when the visible page is full and entirely in-window', () => {
  const saturated = Array.from({ length: FEED_PAGE_LIMIT }, (_, i) =>
    entry('notification_created', `2026-07-16T11:00:${String(i % 60).padStart(2, '0')}Z`),
  );
  assert.equal(window24h(saturated, NOW).truncated, true);
  // A full page whose tail falls OUTSIDE the window is exact, not truncated.
  const withOldTail = [
    ...saturated.slice(0, FEED_PAGE_LIMIT - 1),
    entry('notification_created', '2026-07-01T00:00:00Z'),
  ];
  assert.equal(window24h(withOldTail, NOW).truncated, false);
});

test('hubKpis renders lower-bound counts with a + suffix when the page saturates', () => {
  const saturated = Array.from({ length: FEED_PAGE_LIMIT }, (_, i) =>
    entry(i % 10 === 0 ? 'push_failed' : 'push_sent', '2026-07-16T11:00:00Z'),
  );
  const [, decisions, failures] = hubKpis(grid(), saturated, NOW);
  assert.equal(decisions!.value, '50+');
  assert.equal(failures!.value, '5+');
});

// ---- MANDATORY: KPI tiles only render real-backed metrics -------------------

test('hubKpis emits exactly the three real-backed tiles — no estimated "saved hours" tile', () => {
  const kpis = hubKpis(grid(['security']), [entry('push_failed', '2026-07-16T11:00:00Z')], NOW);
  assert.deepEqual(
    kpis.map((k) => k.label),
    ['ACTIVE RULES', 'DECISIONS · 24H', 'FAILURES · 24H'],
  );
  assert.deepEqual(
    kpis.map((k) => k.value),
    ['3/4', '1', '1'],
  );
  assert.ok(
    kpis.every((k) => !/SAVED|HOURS/i.test(k.label)),
    'no tile may claim the reference\'s estimated saved-hours metric',
  );
});

test('hubKpis shows dashes for the log tiles while the feed is loading', () => {
  assert.deepEqual(
    hubKpis(undefined, undefined, NOW).map((k) => k.value),
    ['—', '—', '—'],
  );
});

// ---- Screen source scans -----------------------------------------------------

const screenSource = readFileSync(
  fileURLToPath(new URL('./screens/AutomationHubScreen.tsx', import.meta.url)),
  'utf8',
);

test('the KPI row renders through hubKpis only — the screen invents no metric of its own', () => {
  assert.ok(screenSource.includes('hubKpis('), 'KPI row must come from the presenter');
  assert.ok(
    !/Saved|hours/i.test(screenSource.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')),
    'no saved-hours tile may appear in the rendered source',
  );
});

test('MANDATORY: the read-only Rules tab gained no toggle control', () => {
  // Case-sensitive on purpose: a rendered control is `Switch`/`Toggle` (an
  // import specifier or JSX tag); the lowercase `switch` statement is fine.
  assert.ok(
    !/\bSwitch\b|\bToggle\b/.test(screenSource.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')),
    'no toggle/Switch may render on a screen with no edit action',
  );
  assert.ok(
    screenSource.includes('Edit these in Settings → Notification preferences.'),
    'the read-only signal caption must survive the rebuild',
  );
});

test('MANDATORY: no hardcoded radius or color literals remain on the screen', () => {
  const code = screenSource.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '');
  assert.ok(
    !/borderRadius:\s*\d/.test(code),
    'all radii must come from t.radius.* — the recon-flagged radius:10 (and the 8) must be gone',
  );
  assert.ok(
    !/#[0-9a-fA-F]{3,8}\b/.test(code) && !/rgba?\(/.test(code),
    'no raw hex/rgba color literals — colors flow through theme tokens and gx',
  );
});
