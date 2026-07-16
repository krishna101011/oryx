/**
 * Automation Hub KPI presenter — design-foundation wave (AH-1, 2026-07-16).
 *
 * Every tile traces to a confirmed real source; the reference's fourth tile
 * ("Saved analyst hours") is deliberately ABSENT — the reference itself labels
 * it "estimated" and no ORYX field measures analyst time, so it is omitted
 * rather than invented (same standard as the Command Center's no-delta tiles).
 *
 *   ACTIVE RULES     — GET /activity/alerts/preferences (the COMPLETE resolved
 *                      category × channel grid; router backfills defaults, so
 *                      the count is exact): categories whose in_app frequency
 *                      is not 'off', over the four real categories.
 *   DECISIONS · 24H  — GET /automation-log entries within the last 24 hours.
 *                      The endpoint returns the newest 50 (backend FEED_LIMIT);
 *                      when the visible page is saturated inside the window the
 *                      count is a LOWER BOUND and renders with a '+' suffix
 *                      instead of pretending to be exact.
 *   FAILURES · 24H   — the *_failed subset of the same window, same honest
 *                      '+' truncation rule. A true failure RATE would need an
 *                      unbounded denominator the API doesn't provide, so the
 *                      reference's "Failure rate" ships as this count instead.
 */
import type { AlertPreference, Automation } from '@oryx/shared-types';
import { ALERT_CATEGORIES } from '../settings/alertCategories';

/** Mirrors apps/backend services/automation/router.py FEED_LIMIT. */
export const FEED_PAGE_LIMIT = 50;

const WINDOW_MS = 24 * 60 * 60 * 1000;

export interface HubKpi {
  label: string;
  value: string;
}

/** 'N/4' — categories whose in-app cadence is on. '—' while loading. */
export function activeRulesValue(prefs: AlertPreference[] | undefined): string {
  if (!prefs) return '—';
  const active = ALERT_CATEGORIES.filter((category) => {
    const row = prefs.find((p) => p.type === category && p.channel === 'in_app');
    return row !== undefined && row.frequency !== 'off';
  }).length;
  return `${active}/${ALERT_CATEGORIES.length}`;
}

interface Window24h {
  decisions: number;
  failures: number;
  /** True when the visible page is full AND entirely inside the window —
   * older same-window entries may exist beyond the page, so counts are
   * lower bounds. */
  truncated: boolean;
}

export function window24h(
  entries: Automation.AutomationLogEntry[],
  now: Date,
): Window24h {
  const cutoff = now.getTime() - WINDOW_MS;
  const inWindow = entries.filter((e) => {
    const at = new Date(e.createdAt).getTime();
    return !Number.isNaN(at) && at >= cutoff;
  });
  return {
    decisions: inWindow.length,
    failures: inWindow.filter((e) => e.action.endsWith('_failed')).length,
    truncated:
      entries.length >= FEED_PAGE_LIMIT && inWindow.length === entries.length,
  };
}

function windowValue(count: number, truncated: boolean): string {
  return truncated ? `${count}+` : String(count);
}

/**
 * The full KPI row — exactly the metrics with real backing, in render order.
 * Loading states show '—', never a fabricated zero.
 */
export function hubKpis(
  prefs: AlertPreference[] | undefined,
  entries: Automation.AutomationLogEntry[] | undefined,
  now: Date,
): HubKpi[] {
  const win = entries ? window24h(entries, now) : null;
  return [
    { label: 'ACTIVE RULES', value: activeRulesValue(prefs) },
    {
      label: 'DECISIONS · 24H',
      value: win ? windowValue(win.decisions, win.truncated) : '—',
    },
    {
      label: 'FAILURES · 24H',
      value: win ? windowValue(win.failures, win.truncated) : '—',
    },
  ];
}
