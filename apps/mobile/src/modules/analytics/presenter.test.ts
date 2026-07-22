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
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  type Series,
  buildFunnel,
  buildKpis,
  computeTrend,
  dayBefore,
  formatDuration,
  formatFunnelDrop,
  formatSuccessRate,
  formatTrend,
  funnelIsEmpty,
  funnelSummary,
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
  assert.equal(kpis.length, 5);
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

test('buildKpis reports the five pipeline-stage headlines', () => {
  const kpis = buildKpis(richSeries, TODAY);
  assert.deepEqual(
    kpis.map((k) => k.key),
    [
      'intake_items_received',
      'claims_verified',
      'drafts_published',
      'notifications_created',
      'emails_sent',
    ],
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

  // Quiet-both with MULTI-day history is still a genuine flat "no change" —
  // recurrence was demonstrated, the quiet is real. (The single-stale-point
  // variant of this case is now 'dormant'; see the trends-wave tests below.)
  const quietBoth: Series = {
    m: [
      { date: '2026-06-08', value: 1 },
      { date: '2026-06-10', value: 2 },
    ],
  };
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
  // intake_items_received's whole observed life is ONE stale day (06-01)
  // with a quiet current window -> dormant since the 2026-07-22 trends wave
  // (previously a misleading "no change" flat).
  assert.deepEqual(kpis.find((k) => k.key === 'intake_items_received')?.trend, {
    kind: 'dormant',
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

// -------------------- trends wave (2026-07-22): emails_sent + dormant --------------------

test('emails_sent is a trended KPI card and its trend computes from real-shaped history', () => {
  // Mirrors the real rollup shape for this metric on 2026-07-22 (7 sparse
  // days spanning both windows), rebased onto the test's TODAY.
  const series: Series = {
    emails_sent: [
      { date: '2026-06-27', value: 276 }, // prior window
      { date: '2026-06-28', value: 84 }, //  prior window -> prior = 360
      { date: '2026-07-02', value: 301 }, // current window
      { date: '2026-07-07', value: 673 }, // current window
      { date: '2026-07-08', value: 905 }, // current window -> current = 1879
    ],
  };
  const card = buildKpis(series, TODAY).find((k) => k.key === 'emails_sent');
  assert.ok(card, 'emails_sent card missing from KPI_DEFS');
  assert.equal(card.label, 'Emails sent');
  assert.equal(card.value, 1879);
  assert.deepEqual(card.trend, {
    kind: 'trend',
    direction: 'up',
    current: 1879,
    prior: 360,
    pctChange: ((1879 - 360) / 360) * 100,
  });
  assert.equal(formatTrend(card.trend)?.text, '▲ 422% vs prior 7 days');
});

test('a single stale observation renders dormant, not a fake 100% decline', () => {
  // The lone point sits in the PRIOR window: pre-fix this computed
  // {direction:'down', pctChange:-100} — a rate-of-change claim about a
  // metric that never recurred (the research_packets_ready shape).
  const inPrior: Series = { m: [{ date: '2026-06-28', value: 2 }] };
  assert.deepEqual(computeTrend(inPrior, 'm', TODAY, 7), { kind: 'dormant' });
  // ...and once the point ages past both windows the state STAYS dormant
  // (pre-fix it decayed into a misleading flat "no change").
  const olderThanBoth: Series = { m: [{ date: '2026-06-10', value: 2 }] };
  assert.deepEqual(computeTrend(olderThanBoth, 'm', TODAY, 7), { kind: 'dormant' });
  assert.deepEqual(formatTrend({ kind: 'dormant' }), {
    text: 'no recent activity',
    tone: 'neutral',
  });
});

test('dormant never suppresses a genuine decline backed by recurring history', () => {
  // TWO observed days before the window -> recurrence demonstrated; a quiet
  // current week is a real 100% decline and must still say so.
  const realDecline: Series = {
    m: [
      { date: '2026-06-26', value: 4 }, // prior window
      { date: '2026-06-30', value: 6 }, // prior window -> prior = 10
    ],
  };
  const trend = computeTrend(realDecline, 'm', TODAY, 7);
  assert.deepEqual(trend, {
    kind: 'trend', direction: 'down', current: 0, prior: 10, pctChange: -100,
  });
  assert.deepEqual(formatTrend(trend), { text: '▼ 100% vs prior 7 days', tone: 'danger' });
});

test('dormant rule regression: "new", insufficient, and active single-day cases unaffected', () => {
  // Single observed day INSIDE the current window: still 'insufficient'
  // (nothing observed before the window), never dormant.
  const young: Series = { m: [{ date: '2026-07-05', value: 12 }] };
  assert.deepEqual(computeTrend(young, 'm', TODAY, 7), { kind: 'insufficient' });
  // Multi-day history with a quiet prior window: still the 'new' rendering.
  const fromNothing: Series = {
    m: [
      { date: '2026-06-10', value: 2 },
      { date: '2026-07-06', value: 5 },
    ],
  };
  assert.equal(formatTrend(computeTrend(fromNothing, 'm', TODAY, 7))?.text, '▲ new vs prior 7 days');
  // Single stale day but a NON-quiet current window cannot exist for one
  // observed day (the day would be in the window) — the nearest real case,
  // one stale + one current day, is a genuine 'new'/trend, not dormant.
  const staleThenActive: Series = {
    m: [
      { date: '2026-06-10', value: 2 },
      { date: '2026-07-03', value: 7 },
    ],
  };
  const trend = computeTrend(staleThenActive, 'm', TODAY, 7);
  assert.ok(trend?.kind === 'trend' && trend.direction === 'up');
});

// -------------------- Funnel drops + summary (AN-3, design-foundation wave) --------------------

/** One same-day point per stage, all inside the 30-day window. */
const funnelSeries = (totals: Record<string, number>): Series =>
  Object.fromEntries(
    Object.entries(totals).map(([key, value]) => [key, [{ date: TODAY, value }]]),
  );

test('funnel drops appear only between genuinely sequential stages, with hand-checked math', () => {
  const stages = buildFunnel(
    funnelSeries({
      claims_extracted: 40,
      claims_typed: 30,
      claims_verified: 24,
      claims_failed: 6,
      evidence_collected: 100,
      conflicts_detected: 10,
      conflicts_resolved: 4,
      intelligence_objects_created: 8,
      intelligence_objects_updated: 12,
      intelligence_objects_reviewed: 5,
      research_packets_ready: 2,
    }),
    TODAY,
    30,
  );
  const byKey = new Map(stages.map((s) => [s.key, s]));
  // Hand-verified: (40-30)/40 = 25%, (30-24)/30 = 20%, (10-4)/10 = 60%.
  assert.equal(byKey.get('claims_typed')!.drop, 25);
  assert.equal(byKey.get('claims_verified')!.drop, 20);
  assert.equal(byKey.get('conflicts_resolved')!.drop, 60);
  // Branch/volume/operation rows must carry NO drop — the arithmetic would
  // be dishonest (failed is a branch, evidence is per-claim volume, the
  // object metrics are distinct operations, packets aggregate claims).
  for (const key of [
    'claims_extracted',
    'claims_failed',
    'evidence_collected',
    'conflicts_detected',
    'intelligence_objects_created',
    'intelligence_objects_updated',
    'intelligence_objects_reviewed',
    'research_packets_ready',
  ]) {
    assert.equal(byKey.get(key)!.drop, null, `${key} must have no drop figure`);
  }
});

test('a zero-total feeder yields no drop figure — no denominator, no percentage', () => {
  const stages = buildFunnel(funnelSeries({ claims_typed: 5 }), TODAY, 30);
  assert.equal(stages.find((s) => s.key === 'claims_typed')!.drop, null);
});

test('a window-edge increase renders signed and neutral, never disguised as a drop', () => {
  // 10 extracted but 12 typed inside the window (predecessors fired before
  // the window opened): drop = (10-12)/10 = -20%.
  const stages = buildFunnel(
    funnelSeries({ claims_extracted: 10, claims_typed: 12 }),
    TODAY,
    30,
  );
  const typed = stages.find((s) => s.key === 'claims_typed')!;
  assert.equal(typed.drop, -20);
  assert.deepEqual(formatFunnelDrop(typed.drop), { text: '+20.0%', tone: 'neutral' });
  assert.deepEqual(formatFunnelDrop(25), { text: '-25.0%', tone: 'danger' });
  assert.equal(formatFunnelDrop(null), null);
});

test('funnel summary is the real extracted→verified conversion, absent without a denominator', () => {
  const stages = buildFunnel(
    funnelSeries({ claims_extracted: 40, claims_typed: 30, claims_verified: 24 }),
    TODAY,
    30,
  );
  // Hand-verified: 24/40 = 60.00%.
  assert.deepEqual(funnelSummary(stages), {
    label: 'EXTRACTED → VERIFIED',
    text: '60.00%',
  });
  const empty = buildFunnel(funnelSeries({ claims_verified: 24 }), TODAY, 30);
  assert.equal(funnelSummary(empty), null);
});

// -------------------- Source scans (AN wave honesty checks) --------------------

const read = (relToRepoRoot: string): string =>
  readFileSync(
    fileURLToPath(new URL(`../../../../../${relToRepoRoot}`, import.meta.url)),
    'utf8',
  );

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '');

test("the KPI sparkline stretches to the tile's full width at 28px height", () => {
  const screen = read(
    'apps/mobile/src/modules/analytics/screens/AnalyticsHomeScreen.tsx',
  );
  assert.ok(
    screen.includes('<Spark data={kpi.spark} fullWidth height={28} />'),
    'the KPI spark must use the full-width micro-spark mode at 28px',
  );
  assert.ok(!screen.includes('width={96}'), 'the fixed 96px spark must be gone');
  const spark = read('packages/design-system/src/components/Spark.tsx');
  assert.ok(
    spark.includes("preserveAspectRatio={fullWidth ? 'none' : undefined}") &&
      spark.includes("fullWidth ? '100%' : width"),
    "Spark's fullWidth mode must stretch via width 100% + preserveAspectRatio none",
  );
});

test('MANDATORY: no hardcoded radius or color literals remain on the Analytics screen', () => {
  const code = stripComments(
    read('apps/mobile/src/modules/analytics/screens/AnalyticsHomeScreen.tsx'),
  );
  assert.ok(
    !/borderRadius:\s*\d/.test(code),
    'all radii must come from t.radius / t.gensparkRadius — the carried-over radius:10/8 must be gone',
  );
  assert.ok(
    !/#[0-9a-fA-F]{3,8}\b/.test(code) && !/rgba?\(/.test(code),
    'no raw hex/rgba color literals — colors flow through theme tokens',
  );
});

test('confirmation: kpiVal typography (AN-1) and BarSeries (AN-4) were not regressed', () => {
  const screen = read(
    'apps/mobile/src/modules/analytics/screens/AnalyticsHomeScreen.tsx',
  );
  // Same invariant foundation.test.ts pins: exactly 3 kpiVal stat values.
  assert.equal(screen.match(/variant="kpiVal"/g)?.length, 3);
  const bars = stripComments(
    read('apps/mobile/src/modules/analytics/components/BarSeries.tsx'),
  );
  // The recon-verified chart grammar markers, all still present:
  assert.ok(bars.includes('border.default'), 'grid stroke = border.default');
  assert.ok(bars.includes('JetBrainsMono_400Regular'), 'axis labels in mono');
  assert.ok(bars.includes('accent.slateBlue'), 'bars = accent.slateBlue');
  assert.ok(
    !/#[0-9a-fA-F]{3,8}\b/.test(bars) && !/rgba?\(/.test(bars),
    'BarSeries stays literal-free',
  );
});
