/**
 * Automation Hub Log-tab presenter — Phase 6 Wave B.
 *
 * Pure mapping from AutomationLogEntry (GET /v1/automation-log) to display
 * rows. No raw enum strings reach the screen: actions, categories, and event
 * types all pass through human copy here. Status tone maps onto the semantic
 * token names the screen resolves against the theme (positive = delivered/
 * healthy, warn = suppressed/degraded, danger = failed, neutral = the rest).
 */
import type { Automation } from '@oryx/shared-types';
import { categoryLabel, humanize } from '../settings/alertCategories';

export type FeedTone = 'positive' | 'warn' | 'danger' | 'neutral';

export interface FeedDetailLine {
  label: string;
  value: string;
}

export interface FeedRow {
  id: string;
  title: string;
  subtitle: string;
  tone: FeedTone;
  icon: 'BellRing' | 'BellOff' | 'Layers' | 'AlertTriangle';
  createdAt: string;
  /** What the row expands to on press — always at least one real line. */
  detail: FeedDetailLine[];
}

const ACTION_COPY: Record<Automation.AutomationAction, { title: string; tone: FeedTone; icon: FeedRow['icon'] }> = {
  notification_created: { title: 'Notification delivered', tone: 'positive', icon: 'BellRing' },
  suppressed_by_preference: { title: 'Suppressed by your preferences', tone: 'warn', icon: 'BellOff' },
  push_sent: { title: 'Push sent', tone: 'positive', icon: 'BellRing' },
  push_failed: { title: 'Push failed', tone: 'danger', icon: 'AlertTriangle' },
  push_suppressed_quiet_hours: { title: 'Push held by quiet hours', tone: 'warn', icon: 'BellOff' },
  email_sent: { title: 'Email sent', tone: 'positive', icon: 'BellRing' },
  email_failed: { title: 'Email failed', tone: 'danger', icon: 'AlertTriangle' },
  email_suppressed_quiet_hours: { title: 'Email held by quiet hours', tone: 'warn', icon: 'BellOff' },
  digest_sent: { title: 'Digest sent', tone: 'positive', icon: 'Layers' },
};

const CHANNEL_COPY: Record<string, string> = {
  in_app: 'In-app',
  push: 'Push',
  email: 'Email',
};

/**
 * Honest copy for a failed action whose row predates reason capture
 * (migration 0024, 2026-07-12) — stated plainly, never invented.
 */
export const REASON_NOT_RECORDED =
  'Not recorded — this entry predates failure-reason capture.';

/**
 * The expanded view's lines — only REAL stored data. Failed actions always
 * get a Reason line: the persisted detail when the row has one, the honest
 * not-recorded copy when it predates capture. Successes/suppressions never
 * get a fabricated reason line.
 */
export function toDetailLines(entry: Automation.AutomationLogEntry): FeedDetailLine[] {
  const lines: FeedDetailLine[] = [];
  if (entry.kind === 'digest') {
    if (entry.windowStart && entry.windowEnd) {
      lines.push({
        label: 'Window',
        value: `${new Date(entry.windowStart).toLocaleString()} → ${new Date(entry.windowEnd).toLocaleString()}`,
      });
    }
    if (entry.category) {
      lines.push({ label: 'Category', value: categoryLabel(entry.category) });
    }
    return lines;
  }

  if (entry.channel) {
    lines.push({ label: 'Channel', value: CHANNEL_COPY[entry.channel] ?? entry.channel });
  }
  if (entry.eventType) {
    lines.push({ label: 'Trigger', value: humanize(entry.eventType) });
  }
  if (entry.action.endsWith('_failed')) {
    lines.push({ label: 'Reason', value: entry.detail ?? REASON_NOT_RECORDED });
  } else if (entry.detail) {
    // Non-failed rows normally carry no detail; surface it if one ever does.
    lines.push({ label: 'Detail', value: entry.detail });
  }
  return lines;
}

export function toFeedRow(entry: Automation.AutomationLogEntry): FeedRow {
  const copy = ACTION_COPY[entry.action] ?? {
    title: humanize(entry.action),
    tone: 'neutral' as const,
    icon: 'BellRing' as const,
  };

  if (entry.kind === 'digest') {
    const cadence =
      entry.frequency === 'weekly' ? 'Weekly digest sent' : 'Daily digest sent';
    return {
      id: entry.id,
      title: cadence,
      subtitle: entry.category ? categoryLabel(entry.category) : '',
      tone: copy.tone,
      icon: 'Layers',
      createdAt: entry.createdAt,
      detail: toDetailLines(entry),
    };
  }

  return {
    id: entry.id,
    title: copy.title,
    subtitle: entry.eventType ? humanize(entry.eventType) : '',
    tone: copy.tone,
    icon: copy.icon,
    createdAt: entry.createdAt,
    detail: toDetailLines(entry),
  };
}

/** Presenter for the whole feed — API order is already newest-first, but the
 * merge invariant matters to the screen, so it is re-asserted here. */
export function toFeedRows(entries: Automation.AutomationLogEntry[]): FeedRow[] {
  return entries
    .map(toFeedRow)
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
}
