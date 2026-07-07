/**
 * Human copy for the alert-preference grid — Phase 6 Wave B.
 *
 * The four REAL alert_preferences categories (services/activity/preferences.py
 * NOTIFICATION_CATEGORIES; the cadence-label activity_type values are never
 * used on alert_preferences). Raw enum strings must never render on screen —
 * every category and frequency goes through these maps.
 */
import type { NotificationFrequency } from '@oryx/shared-types';

export const ALERT_CATEGORIES = [
  'security',
  'system',
  'verification',
  'publishing',
] as const;

export type AlertCategory = (typeof ALERT_CATEGORIES)[number];

export const CATEGORY_COPY: Record<AlertCategory, { label: string; description: string }> = {
  security: {
    label: 'Security alerts',
    description: 'Sign-ins, password and account changes.',
  },
  system: {
    label: 'System updates',
    description: 'Source intake and platform activity.',
  },
  verification: {
    label: 'Verification alerts',
    description: 'Conflicts, failed claims, and new evidence.',
  },
  publishing: {
    label: 'Publishing alerts',
    description: 'Drafts, approvals, and scheduled posts.',
  },
};

export const FREQUENCY_COPY: Record<NotificationFrequency, { label: string; description: string }> = {
  off: { label: 'Off', description: 'No notifications for this category.' },
  instant: { label: 'Instant', description: 'As it happens.' },
  daily: { label: 'Daily digest', description: 'Bundled every morning at 8:00.' },
  weekly: { label: 'Weekly digest', description: 'Bundled Monday mornings at 8:00.' },
};

/** Display label for a category; unknown values are humanized, never raw. */
export function categoryLabel(type: string): string {
  const copy = CATEGORY_COPY[type as AlertCategory];
  if (copy) return copy.label;
  return humanize(type);
}

/** 'content.publish.failed' / 'daily_digest' → 'Content publish failed' / 'Daily digest'. */
export function humanize(value: string): string {
  const words = value.replace(/[._]/g, ' ').trim();
  return words.length === 0 ? value : words.charAt(0).toUpperCase() + words.slice(1);
}
