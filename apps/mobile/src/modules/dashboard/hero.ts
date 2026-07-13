import type { IntakeStatusSummary, MeResponse } from '@oryx/shared-types';

/**
 * Command Center hero presenters — pure, node:test-testable (the screen-logic
 * extraction convention, same as stats.ts).
 *
 * The hero shows a real date/time kicker and an honest one-sentence summary
 * built ONLY from confirmed real fields: IntakeStatusSummary.total (GET
 * /intake/status), MeResponse.verification.pendingReviewCount and
 * MeResponse.content.draftCount (GET /auth/me). Nothing here invents a
 * number: a query that hasn't resolved renders an em dash (the established
 * never-flash-a-fake-zero stat rule), and a real zero renders as "0".
 */

const WEEKDAYS = [
  'SUNDAY',
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
] as const;

const MONTHS = [
  'JAN',
  'FEB',
  'MAR',
  'APR',
  'MAY',
  'JUN',
  'JUL',
  'AUG',
  'SEP',
  'OCT',
  'NOV',
  'DEC',
] as const;

const pad2 = (n: number): string => String(n).padStart(2, '0');

/**
 * The reference hero kicker ("FRIDAY · JUN 28 · 07:48 ET",
 * command-center.jsx:50) built from a real Date — device-local time, 24h.
 * The timezone suffix is deliberately dropped: RN has no reliable
 * cross-platform short-zone name, and a wrong "ET" would be styled data.
 * Takes `now` as a parameter (never reads the clock itself) so tests are
 * deterministic.
 */
export function heroKicker(now: Date): string {
  const weekday = WEEKDAYS[now.getDay()];
  const month = MONTHS[now.getMonth()];
  return `${weekday} · ${month} ${pad2(now.getDate())} · ${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
}

/** One run of the summary sentence; `strong` segments are the real numbers
 * (rendered in primary text over the secondary sentence, per the reference's
 * highlighted counts). */
export interface SummarySegment {
  text: string;
  strong: boolean;
}

/** '3' for a loaded count, '—' while the owning query has no data yet. */
const count = (n: number | undefined): string => (n === undefined ? '—' : String(n));

/** Singular for exactly 1; the em-dash placeholder reads as plural. */
const word = (n: number | undefined, singular: string, plural: string): string =>
  n === 1 ? singular : plural;

/**
 * The honest hero sentence:
 *   "19 sources connected, 4 claims awaiting review, and 2 drafts in progress."
 * Always returned — a zero is stated plainly, never hidden; an unresolved
 * query shows '—' for its number only.
 */
export function heroSummary(
  status: Pick<IntakeStatusSummary, 'total'> | undefined,
  me: Pick<MeResponse, 'verification' | 'content'> | undefined,
): SummarySegment[] {
  const sources = status?.total;
  const claims = me?.verification.pendingReviewCount;
  const drafts = me?.content.draftCount;
  return [
    { text: count(sources), strong: true },
    { text: ` ${word(sources, 'source', 'sources')} connected, `, strong: false },
    { text: count(claims), strong: true },
    { text: ` ${word(claims, 'claim', 'claims')} awaiting review, and `, strong: false },
    { text: count(drafts), strong: true },
    { text: ` ${word(drafts, 'draft', 'drafts')} in progress.`, strong: false },
  ];
}
