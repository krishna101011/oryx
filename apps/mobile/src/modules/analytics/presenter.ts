/**
 * Analytics presenter — Phase 7 Wave B.
 *
 * Pure view-model logic for the Analytics screen, kept out of the component
 * so it is testable with the node test runner (same pattern as
 * modules/automation/feed.ts). Everything here handles the near-empty-history
 * case explicitly: Wave A only just shipped, so a workspace with NO rollup
 * rows at all is the NORMAL state, not an edge case — the screen shows a
 * "still gathering" state instead of a wall of zeros.
 *
 * All date math takes `today` as a parameter (never reads the clock itself)
 * so tests are deterministic.
 */
import type { Analytics } from '@oryx/shared-types';

export type Series = Record<string, Analytics.RollupPoint[]>;

/** UTC YYYY-MM-DD for a Date. */
const isoDay = (d: Date): string => d.toISOString().slice(0, 10);

/** The UTC day `offset` days before `today` (an ISO YYYY-MM-DD string). */
export function dayBefore(today: string, offset: number): string {
  const d = new Date(`${today}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - offset);
  return isoDay(d);
}

/** True when at least one metric has at least one point — the gate between
 * the real dashboard and the still-gathering state. */
export function hasAnyData(series: Series): boolean {
  return Object.values(series).some((points) => points.length > 0);
}

/** Sum of a metric over the trailing `days` window ending at `today`,
 * inclusive. Returns null when the metric has no points AT ALL in the
 * response (absent ≠ zero: absent means nothing measured yet). */
export function sumWindow(
  series: Series,
  key: string,
  today: string,
  days: number,
): number | null {
  const points = series[key];
  if (!points || points.length === 0) return null;
  const from = dayBefore(today, days - 1);
  return points
    .filter((p) => p.date >= from && p.date <= today)
    .reduce((acc, p) => acc + p.value, 0);
}

/** Zero-padded daily values over the trailing `days` window (ascending) —
 * sparse rollups in, dense chart data out. */
export function padDailySeries(
  series: Series,
  key: string,
  today: string,
  days: number,
): number[] {
  const byDate = new Map((series[key] ?? []).map((p) => [p.date, p.value]));
  const out: number[] = [];
  for (let i = days - 1; i >= 0; i--) {
    out.push(byDate.get(dayBefore(today, i)) ?? 0);
  }
  return out;
}

// -------------------- KPI cards --------------------

export interface Kpi {
  key: string;
  label: string;
  /** 7-day total; null = metric entirely absent (render an em dash, not 0). */
  value: number | null;
  /** 14-day zero-padded daily values for the card sparkline. */
  spark: number[];
  /** Wave C: current 7-day window vs the prior 7; null = metric absent. */
  trend: Trend | null;
}

/**
 * The four headline KPIs — one per pipeline stage, so the row answers "is the
 * whole machine running" at a glance: intake (is anything coming in) →
 * verification (is the engine producing verified intelligence — the
 * platform's core value) → publishing (is real output leaving the building) →
 * automation (is the system talking to the user).
 */
export const KPI_DEFS: { key: string; label: string }[] = [
  { key: 'intake_items_received', label: 'Items ingested' },
  { key: 'claims_verified', label: 'Claims verified' },
  { key: 'drafts_published', label: 'Drafts published' },
  { key: 'notifications_created', label: 'Notifications' },
];

export const KPI_WINDOW_DAYS = 7;
export const SPARK_WINDOW_DAYS = 14;
export const CHART_WINDOW_DAYS = 30;

export function buildKpis(series: Series, today: string): Kpi[] {
  return KPI_DEFS.map(({ key, label }) => ({
    key,
    label,
    value: sumWindow(series, key, today, KPI_WINDOW_DAYS),
    spark: padDailySeries(series, key, today, SPARK_WINDOW_DAYS),
    trend: computeTrend(series, key, today, KPI_WINDOW_DAYS),
  }));
}

// -------------------- Trend (Wave C) --------------------

export type TrendDirection = 'up' | 'down' | 'flat';

/**
 * Trend for one KPI: the current trailing window vs the window immediately
 * before it, computed on read from the SAME rollups response the cards
 * already hold (the default /analytics/rollups range is 30 days; both 7-day
 * windows sit inside it). Nothing is persisted.
 *
 * 'insufficient': the metric has points, but none dated before the current
 * window — its entire observed life fits inside the window, so there is no
 * prior period to compare against yet. Distinct from a REAL zero prior sum
 * (points exist before the window but the prior week was quiet), same
 * absent ≠ zero discipline as sumWindow.
 */
export type Trend =
  | { kind: 'insufficient' }
  | {
      kind: 'trend';
      direction: TrendDirection;
      current: number;
      prior: number;
      /** Percent change vs prior; null when prior === 0 and current > 0
       * (grew from nothing — no denominator, rendered as "new"). */
      pctChange: number | null;
    };

/** null = metric entirely absent from the response (no trend row at all —
 * the card already renders an em dash for the value). */
export function computeTrend(
  series: Series,
  key: string,
  today: string,
  days: number,
): Trend | null {
  const points = series[key];
  if (!points || points.length === 0) return null;
  const currentFrom = dayBefore(today, days - 1);
  if (!points.some((p) => p.date < currentFrom)) return { kind: 'insufficient' };
  const sum = (from: string, to: string): number =>
    points
      .filter((p) => p.date >= from && p.date <= to)
      .reduce((acc, p) => acc + p.value, 0);
  const current = sum(currentFrom, today);
  const prior = sum(dayBefore(today, 2 * days - 1), dayBefore(today, days));
  const direction: TrendDirection =
    current > prior ? 'up' : current < prior ? 'down' : 'flat';
  const pctChange =
    prior > 0 ? ((current - prior) / prior) * 100 : current === 0 ? 0 : null;
  return { kind: 'trend', direction, current, prior, pctChange };
}

export interface TrendDisplay {
  text: string;
  /** Matches the automation feed's tone convention (FeedTone colors). */
  tone: 'positive' | 'danger' | 'neutral';
}

/** Renderable copy for a KPI card's trend row. null = metric absent, render
 * no row (absent stays visually distinct from "no change"). */
export function formatTrend(trend: Trend | null): TrendDisplay | null {
  if (trend === null) return null;
  if (trend.kind === 'insufficient') {
    return { text: 'not enough history yet', tone: 'neutral' };
  }
  const vs = `vs prior ${KPI_WINDOW_DAYS} days`;
  if (trend.direction === 'flat') return { text: `no change ${vs}`, tone: 'neutral' };
  const arrow = trend.direction === 'up' ? '▲' : '▼';
  const tone = trend.direction === 'up' ? 'positive' : 'danger';
  if (trend.pctChange === null) return { text: `${arrow} new ${vs}`, tone };
  const rounded = Math.round(Math.abs(trend.pctChange));
  // A real-but-tiny change must never read as the flat state's "no change".
  const amount = rounded === 0 ? '<1%' : `${rounded}%`;
  return { text: `${arrow} ${amount} ${vs}`, tone };
}

// -------------------- Research funnel --------------------

export interface FunnelStage {
  key: string;
  label: string;
  total: number;
  /** total / max stage total — drives the proportional bar width. */
  ratio: number;
  /**
   * Percent change vs the stage that genuinely FEEDS this one (AN-3,
   * design-foundation wave): positive = a drop, negative = the window-edge
   * case where an event's successor lands inside the window but the
   * predecessor fired before it (rendered signed, never disguised). null =
   * no honest predecessor exists (see FUNNEL_DEFS) or the predecessor total
   * is 0 (no denominator).
   */
  drop: number | null;
}

/**
 * §3.3's verification/research funnel in pipeline order — claims flow in at
 * the top, verified intelligence and research packets come out the bottom.
 * research_packets_ready is the only direct research-usage signal that
 * exists; the frozen doc forbids a research view without it.
 *
 * `dropFrom` names the stage that GENUINELY feeds a stage, so the reference's
 * per-stage drop figure (analytics.jsx:65) is only computed where the
 * arithmetic is honest: extracted→typed→verified is the real claims pipeline
 * (verification.claim.* event chain) and resolved ⊂ detected for conflicts.
 * Everything else deliberately carries none: claims_failed is the FAILURE
 * BRANCH of typing/verification (not fed by claims_verified), evidence rows
 * are per-claim volume (can exceed claim counts), the three object metrics
 * are distinct operations on the same entities (updated is not a subset of
 * created within a window), and a research packet aggregates many claims —
 * none of those adjacent pairs form a conversion a drop%% could describe.
 */
export const FUNNEL_DEFS: { key: string; label: string; dropFrom?: string }[] = [
  { key: 'claims_extracted', label: 'Claims extracted' },
  { key: 'claims_typed', label: 'Claims typed', dropFrom: 'claims_extracted' },
  { key: 'claims_verified', label: 'Claims verified', dropFrom: 'claims_typed' },
  { key: 'claims_failed', label: 'Claims failed' },
  { key: 'evidence_collected', label: 'Evidence collected' },
  { key: 'conflicts_detected', label: 'Conflicts detected' },
  { key: 'conflicts_resolved', label: 'Conflicts resolved', dropFrom: 'conflicts_detected' },
  { key: 'intelligence_objects_created', label: 'Objects created' },
  { key: 'intelligence_objects_updated', label: 'Objects updated' },
  { key: 'intelligence_objects_reviewed', label: 'Objects reviewed' },
  { key: 'research_packets_ready', label: 'Research packets ready' },
];

export function buildFunnel(series: Series, today: string, days: number): FunnelStage[] {
  const totals = FUNNEL_DEFS.map(({ key, label, dropFrom }) => ({
    key,
    label,
    dropFrom,
    total: sumWindow(series, key, today, days) ?? 0,
  }));
  const max = Math.max(...totals.map((s) => s.total), 0);
  const byKey = new Map(totals.map((s) => [s.key, s.total]));
  return totals.map(({ dropFrom, ...s }) => {
    const feeder = dropFrom !== undefined ? (byKey.get(dropFrom) ?? 0) : 0;
    return {
      ...s,
      ratio: max > 0 ? s.total / max : 0,
      drop:
        dropFrom !== undefined && feeder > 0
          ? ((feeder - s.total) / feeder) * 100
          : null,
    };
  });
}

export interface FunnelDropDisplay {
  text: string;
  /** danger = a real drop (the reference's neg style); neutral = the honest
   * signed window-edge increase. */
  tone: 'danger' | 'neutral';
}

/** Renderable per-stage drop (reference analytics.jsx:71's `-N.N%` column).
 * null = render no figure at all for this stage. */
export function formatFunnelDrop(drop: number | null): FunnelDropDisplay | null {
  if (drop === null) return null;
  if (drop >= 0) return { text: `-${drop.toFixed(1)}%`, tone: 'danger' };
  return { text: `+${Math.abs(drop).toFixed(1)}%`, tone: 'neutral' };
}

export interface FunnelSummary {
  /** Mono uppercase left label (reference "VISITOR → PAID"). */
  label: string;
  /** e.g. "60.00%" — verified as a share of extracted. */
  text: string;
}

/**
 * The bottom summary row (reference analytics.jsx:79-82's first→last
 * conversion). The honest ORYX end-to-end figure is claims extracted →
 * claims verified: the real conversion of the sequential claims chain.
 * It deliberately does NOT run to research_packets_ready — a packet
 * aggregates many claims, so claims:packets is not a conversion rate.
 * null when nothing was extracted in the window (no denominator).
 */
export function funnelSummary(stages: FunnelStage[]): FunnelSummary | null {
  const extracted = stages.find((s) => s.key === 'claims_extracted')?.total ?? 0;
  const verified = stages.find((s) => s.key === 'claims_verified')?.total ?? 0;
  if (extracted <= 0) return null;
  return {
    label: 'EXTRACTED → VERIFIED',
    text: `${((verified / extracted) * 100).toFixed(2)}%`,
  };
}

/** True when no funnel stage has any activity — the research tab's
 * still-gathering gate. */
export function funnelIsEmpty(stages: FunnelStage[]): boolean {
  return stages.every((s) => s.total === 0);
}

// -------------------- Publishing --------------------

/** '87%' | null when there were no delivery attempts (render "no deliveries
 * yet", never "0%": zero attempts is not a zero success rate). */
export function formatSuccessRate(success: Analytics.PublishingSuccess): string | null {
  if (success.successRate === null) return null;
  return `${Math.round(success.successRate * 100)}%`;
}

/** '4h 12m' / '38m' / '52s' | null when no publications exist yet. */
export function formatDuration(seconds: number | null): string | null {
  if (seconds === null) return null;
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest > 0 ? `${hours}h ${rest}m` : `${hours}h`;
}
