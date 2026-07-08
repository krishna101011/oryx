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
  }));
}

// -------------------- Research funnel --------------------

export interface FunnelStage {
  key: string;
  label: string;
  total: number;
  /** total / max stage total — drives the proportional bar width. */
  ratio: number;
}

/**
 * §3.3's verification/research funnel in pipeline order — claims flow in at
 * the top, verified intelligence and research packets come out the bottom.
 * research_packets_ready is the only direct research-usage signal that
 * exists; the frozen doc forbids a research view without it.
 */
export const FUNNEL_DEFS: { key: string; label: string }[] = [
  { key: 'claims_extracted', label: 'Claims extracted' },
  { key: 'claims_typed', label: 'Claims typed' },
  { key: 'claims_verified', label: 'Claims verified' },
  { key: 'claims_failed', label: 'Claims failed' },
  { key: 'evidence_collected', label: 'Evidence collected' },
  { key: 'conflicts_detected', label: 'Conflicts detected' },
  { key: 'conflicts_resolved', label: 'Conflicts resolved' },
  { key: 'intelligence_objects_created', label: 'Objects created' },
  { key: 'intelligence_objects_updated', label: 'Objects updated' },
  { key: 'intelligence_objects_reviewed', label: 'Objects reviewed' },
  { key: 'research_packets_ready', label: 'Research packets ready' },
];

export function buildFunnel(series: Series, today: string, days: number): FunnelStage[] {
  const totals = FUNNEL_DEFS.map(({ key, label }) => ({
    key,
    label,
    total: sumWindow(series, key, today, days) ?? 0,
  }));
  const max = Math.max(...totals.map((s) => s.total), 0);
  return totals.map((s) => ({ ...s, ratio: max > 0 ? s.total / max : 0 }));
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
