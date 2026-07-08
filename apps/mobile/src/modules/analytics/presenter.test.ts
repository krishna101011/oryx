/**
 * Phase 7 Wave B — Analytics screen presenter.
 *
 * Exercises the pure view-model layer with realistic GET /v1/analytics/rollups
 * payloads (sparse series, exactly what the backend emits). The near-empty-
 * history coverage here is the frontend half of the Wave B mandatory
 * scenario 3: Phase 0 found dev's rollup table completely empty, so the
 * still-gathering path is the screen's NORMAL first render, not an edge case —
 * every helper must handle an empty/absent series without throwing and
 * without dressing "nothing measured yet" up as a hard zero.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  type Series,
  buildFunnel,
  buildKpis,
  dayBefore,
  formatDuration,
  formatSuccessRate,
  funnelIsEmpty,
  hasAnyData,
  padDailySeries,
  sumWindow,
} from './presenter';

const TODAY = '2026-07-08';

const richSeries: Series = {
  claims_verified: [
    { date: '2026-07-05', value: 3 },
    { date: '2026-07-07', value: 5 }, // 07-06 missing: sparse day
  ],
  intake_items_received: [{ date: '2026-06-01', value: 9 }], // outside 7d window
};

// -------------------- near-empty history (mandatory scenario 3) --------------------

test('a completely empty series map renders as the gathering state, not a crash', () => {
  const empty: Series = {};
  assert.equal(hasAnyData(empty), false);
  const kpis = buildKpis(empty, TODAY);
  assert.equal(kpis.length, 4);
  // Absent metric => null (an em dash on screen), NEVER a confusing hard 0.
  assert.ok(kpis.every((k) => k.value === null));
  // Sparklines still get dense zero data — no NaN, no broken chart.
  assert.ok(kpis.every((k) => k.spark.length === 14 && k.spark.every((v) => v === 0)));
  const funnel = buildFunnel(empty, TODAY, 30);
  assert.equal(funnelIsEmpty(funnel), true);
  assert.ok(funnel.every((s) => s.ratio === 0)); // no divide-by-zero NaN
});

test('a metric key present with an empty points array still counts as no data', () => {
  const hollow: Series = { claims_verified: [] };
  assert.equal(hasAnyData(hollow), false);
  assert.equal(sumWindow(hollow, 'claims_verified', TODAY, 7), null);
});

// -------------------- windowing over sparse series --------------------

test('sumWindow sums only points inside the trailing window', () => {
  assert.equal(sumWindow(richSeries, 'claims_verified', TODAY, 7), 8);
  // The 2026-06-01 point is outside the trailing 7 days -> a real 0, because
  // the metric HAS been measured (present key), there was just no activity.
  assert.equal(sumWindow(richSeries, 'intake_items_received', TODAY, 7), 0);
  // Entirely absent metric -> null.
  assert.equal(sumWindow(richSeries, 'drafts_published', TODAY, 7), null);
});

test('padDailySeries zero-fills missing days, ascending, dense', () => {
  const padded = padDailySeries(richSeries, 'claims_verified', TODAY, 5);
  // 07-04..07-08: only 07-05 (3) and 07-07 (5) have rows.
  assert.deepEqual(padded, [0, 3, 0, 5, 0]);
});

test('dayBefore does UTC calendar math across month boundaries', () => {
  assert.equal(dayBefore('2026-07-01', 1), '2026-06-30');
  assert.equal(dayBefore('2026-07-08', 0), '2026-07-08');
});

// -------------------- KPIs --------------------

test('buildKpis reports the four pipeline-stage headlines', () => {
  const kpis = buildKpis(richSeries, TODAY);
  assert.deepEqual(
    kpis.map((k) => k.key),
    ['intake_items_received', 'claims_verified', 'drafts_published', 'notifications_created'],
  );
  const verified = kpis.find((k) => k.key === 'claims_verified');
  assert.equal(verified?.value, 8);
  assert.equal(verified?.spark.length, 14);
});

// -------------------- research funnel --------------------

test('buildFunnel scales stages against the max stage, pipeline order preserved', () => {
  const series: Series = {
    claims_extracted: [{ date: '2026-07-07', value: 40 }],
    claims_verified: [{ date: '2026-07-07', value: 10 }],
    research_packets_ready: [{ date: '2026-07-07', value: 2 }],
  };
  const funnel = buildFunnel(series, TODAY, 30);
  assert.equal(funnelIsEmpty(funnel), false);
  assert.equal(funnel[0]?.key, 'claims_extracted');
  assert.equal(funnel[0]?.ratio, 1);
  const verified = funnel.find((s) => s.key === 'claims_verified');
  assert.equal(verified?.ratio, 0.25);
  const packets = funnel.find((s) => s.key === 'research_packets_ready');
  assert.equal(packets?.total, 2);
  // Stages with no data ride along at zero — visible in the funnel as absent
  // activity, which IS the "where is activity concentrated" signal.
  const typed = funnel.find((s) => s.key === 'claims_typed');
  assert.equal(typed?.total, 0);
});

// -------------------- publishing formatting --------------------

test('formatSuccessRate: null attempts stay null (never rendered as 0%)', () => {
  assert.equal(formatSuccessRate({ published: 0, failed: 0, successRate: null }), null);
  assert.equal(formatSuccessRate({ published: 8, failed: 2, successRate: 0.8 }), '80%');
});

test('formatDuration covers seconds, minutes, hours, and the no-data null', () => {
  assert.equal(formatDuration(null), null);
  assert.equal(formatDuration(52), '52s');
  assert.equal(formatDuration(38 * 60), '38m');
  assert.equal(formatDuration(4 * 3600 + 12 * 60), '4h 12m');
  assert.equal(formatDuration(2 * 3600), '2h');
});
