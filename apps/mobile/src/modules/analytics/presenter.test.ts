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
  computeTrend,
  dayBefore,
  formatDuration,
  formatSuccessRate,
  formatTrend,
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

// -------------------- trend (Wave C) --------------------
// With TODAY = 2026-07-08 and a 7-day window:
//   current window: 2026-07-02 .. 2026-07-08 (inclusive)
//   prior window:   2026-06-25 .. 2026-07-01 (inclusive)

test('trend classifies up, down, and flat against seeded two-window data', () => {
  const up: Series = {
    m: [
      { date: '2026-06-26', value: 3 }, // prior
      { date: '2026-06-30', value: 5 }, // prior  -> prior = 8
      { date: '2026-07-03', value: 4 }, // current
      { date: '2026-07-07', value: 6 }, // current -> current = 10
    ],
  };
  const down: Series = {
    m: [
      { date: '2026-06-25', value: 10 }, // prior = 10
      { date: '2026-07-02', value: 7 }, //  current = 7
    ],
  };
  const flat: Series = {
    m: [
      { date: '2026-06-28', value: 5 }, // prior = 5
      { date: '2026-07-04', value: 5 }, // current = 5
    ],
  };
  assert.deepEqual(computeTrend(up, 'm', TODAY, 7), {
    kind: 'trend', direction: 'up', current: 10, prior: 8, pctChange: 25,
  });
  assert.deepEqual(computeTrend(down, 'm', TODAY, 7), {
    kind: 'trend', direction: 'down', current: 7, prior: 10, pctChange: -30,
  });
  assert.deepEqual(computeTrend(flat, 'm', TODAY, 7), {
    kind: 'trend', direction: 'flat', current: 5, prior: 5, pctChange: 0,
  });
});

test('percentage math verified by hand: (current - prior) / prior * 100', () => {
  // 8 -> 10: change 2, 2/8 = 0.25 -> +25%. 10 -> 7: -3, -3/10 = -0.3 -> -30%.
  // Deliberately re-derived here rather than trusting the values above.
  assert.equal(((10 - 8) / 8) * 100, 25);
  assert.equal(((7 - 10) / 10) * 100, -30);
  // Non-round case: 3 -> 4 is +33.33..%, must round to 33 in copy.
  const trend = computeTrend(
    {
      m: [
        { date: '2026-06-27', value: 3 },
        { date: '2026-07-05', value: 4 },
      ],
    },
    'm', TODAY, 7,
  );
  assert.ok(trend?.kind === 'trend');
  assert.ok(Math.abs(trend.pctChange! - 100 / 3) < 1e-9);
  assert.equal(formatTrend(trend)?.text, '▲ 33% vs prior 7 days');
});

test('window boundaries: 07-01 belongs to prior, 07-02 to current', () => {
  const series: Series = {
    m: [
      { date: '2026-07-01', value: 4 }, // last prior day
      { date: '2026-07-02', value: 9 }, // first current day
    ],
  };
  assert.deepEqual(computeTrend(series, 'm', TODAY, 7), {
    kind: 'trend', direction: 'up', current: 9, prior: 4, pctChange: 125,
  });
});

test('no-prior-data degrades to "not enough history yet", never 0% or an error', () => {
  // Entire observed life inside the current window -> insufficient.
  const young: Series = { m: [{ date: '2026-07-05', value: 12 }] };
  assert.deepEqual(computeTrend(young, 'm', TODAY, 7), { kind: 'insufficient' });
  assert.deepEqual(formatTrend({ kind: 'insufficient' }), {
    text: 'not enough history yet',
    tone: 'neutral',
  });
  // Boundary: earliest point exactly on the current window's first day is
  // still insufficient — nothing was observed BEFORE the window.
  const edge: Series = { m: [{ date: '2026-07-02', value: 1 }] };
  assert.deepEqual(computeTrend(edge, 'm', TODAY, 7), { kind: 'insufficient' });
  // Absent metric -> null trend -> no row at all (absent stays distinct from
  // both "no change" and "not enough history").
  assert.equal(computeTrend(young, 'other_metric', TODAY, 7), null);
  assert.equal(formatTrend(null), null);
});

test('grew-from-quiet prior renders as "new" (no fake percentage), quiet-both as no change', () => {
  // History exists (06-10, before the prior window) so the prior period WAS
  // observable — its zero is a real quiet week, not missing history.
  const fromNothing: Series = {
    m: [
      { date: '2026-06-10', value: 2 },
      { date: '2026-07-06', value: 5 },
    ],
  };
  const trend = computeTrend(fromNothing, 'm', TODAY, 7);
  assert.deepEqual(trend, {
    kind: 'trend', direction: 'up', current: 5, prior: 0, pctChange: null,
  });
  assert.deepEqual(formatTrend(trend), { text: '▲ new vs prior 7 days', tone: 'positive' });

  const quietBoth: Series = { m: [{ date: '2026-06-10', value: 2 }] };
  assert.deepEqual(formatTrend(computeTrend(quietBoth, 'm', TODAY, 7)), {
    text: 'no change vs prior 7 days',
    tone: 'neutral',
  });
});

test('a tiny real change reads as <1%, never as the flat state\'s "no change"', () => {
  const series: Series = {
    m: [
      { date: '2026-06-26', value: 1000 },
      { date: '2026-07-03', value: 1001 },
    ],
  };
  const display = formatTrend(computeTrend(series, 'm', TODAY, 7));
  assert.deepEqual(display, { text: '▲ <1% vs prior 7 days', tone: 'positive' });
});

test('buildKpis carries a trend per card, consistent with its own series', () => {
  const kpis = buildKpis(richSeries, TODAY);
  // claims_verified's points (07-05, 07-07) all sit inside the current window.
  assert.deepEqual(kpis.find((k) => k.key === 'claims_verified')?.trend, {
    kind: 'insufficient',
  });
  // intake_items_received has real pre-window history (06-01) and zero
  // activity in both windows -> a true flat, not "insufficient".
  assert.deepEqual(kpis.find((k) => k.key === 'intake_items_received')?.trend, {
    kind: 'trend', direction: 'flat', current: 0, prior: 0, pctChange: 0,
  });
  // Absent metrics carry no trend at all.
  assert.equal(kpis.find((k) => k.key === 'drafts_published')?.trend, null);
});

test('trend derives only from the series passed in — cross-workspace isolation lives at the endpoint', () => {
  // The rollups response is already workspace-scoped server-side
  // (test_rollups_endpoint_is_workspace_isolated). Client-side, the contract
  // is purity: same input -> same output, and one workspace's series can
  // never influence another's trend because nothing else is read.
  const workspaceA: Series = {
    m: [
      { date: '2026-06-28', value: 2 },
      { date: '2026-07-04', value: 6 },
    ],
  };
  const workspaceB: Series = {
    m: [
      { date: '2026-06-28', value: 500 },
      { date: '2026-07-04', value: 1 },
    ],
  };
  const first = computeTrend(workspaceA, 'm', TODAY, 7);
  computeTrend(workspaceB, 'm', TODAY, 7); // interleaved "other workspace" read
  const second = computeTrend(workspaceA, 'm', TODAY, 7);
  assert.deepEqual(first, second);
  assert.deepEqual(second, {
    kind: 'trend', direction: 'up', current: 6, prior: 2, pctChange: 200,
  });
});
