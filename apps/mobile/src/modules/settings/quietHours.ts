/**
 * Quiet-hours presets for Notification Preferences — Phase 6 Wave C.
 *
 * Wave B deliberately deferred this control; it lands here as a ChoiceTile
 * preset list (the screen's established selection pattern) rather than a
 * novel time-picker widget. Pure TS (no react-native imports) so the mapping
 * logic runs under node's test runner via tsx.
 *
 * "Off" is encoded as start === end (an empty window): the PUT endpoint only
 * writes quiet_hours when a value is present, so a null can never clear an
 * existing window — the backend evaluator (services/activity/quiet_hours.py)
 * treats an equal start/end as "never quiet" by the same documented
 * convention.
 */
import type { QuietHours } from '@oryx/shared-types';

export interface QuietHoursPreset {
  key: 'off' | 'night' | 'evening' | 'late';
  label: string;
  description: string;
  start: string; // 'HH:mm'
  end: string;
}

export const QUIET_HOURS_PRESETS: readonly QuietHoursPreset[] = [
  {
    key: 'off',
    label: 'Off',
    description: 'Push notifications can arrive at any hour.',
    start: '00:00',
    end: '00:00',
  },
  {
    key: 'night',
    label: '10 PM – 7 AM',
    description: 'Quiet overnight; pushes resume in the morning.',
    start: '22:00',
    end: '07:00',
  },
  {
    key: 'evening',
    label: '9 PM – 8 AM',
    description: 'A longer wind-down and slower morning.',
    start: '21:00',
    end: '08:00',
  },
  {
    key: 'late',
    label: '11 PM – 6 AM',
    description: 'Only the deepest hours stay quiet.',
    start: '23:00',
    end: '06:00',
  },
] as const;

/** Which preset a stored value corresponds to. Empty/missing windows are
 * 'off'; a hand-set window that matches no preset reads as null (the screen
 * then highlights nothing rather than lying). */
export function presetKeyFor(
  value: QuietHours | null | undefined,
): QuietHoursPreset['key'] | null {
  if (!value || value.start === value.end) return 'off';
  const match = QUIET_HOURS_PRESETS.find(
    (p) => p.start === value.start && p.end === value.end,
  );
  return match ? match.key : null;
}

export function buildQuietHours(preset: QuietHoursPreset, tz: string): QuietHours {
  return { start: preset.start, end: preset.end, tz };
}

/** The device's IANA timezone — what "10 PM" means to this user. */
export function deviceTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}
