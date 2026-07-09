/**
 * Automation domain types — Phase 6 Wave B.
 *
 * The Automation Hub's transparency feed (docs/PHASE_6_ARCHITECTURE.md §5,
 * GET /v1/automation-log): a reverse-chronological merge of two tables —
 * automation_log (one row per dispatcher decision, including suppressions)
 * and digest_runs (one row per sent digest window). `kind` discriminates.
 */
import type { Id, Timestamp } from './common';
import type { NotificationFrequency } from './preferences';

export type AutomationEntryKind = 'dispatch' | 'digest';

/**
 * automation_log.action_taken vocabulary (§3.4) plus the synthetic
 * 'digest_sent' used for digest_runs entries. push_sent/push_failed are
 * Wave C vocabulary; push_suppressed_quiet_hours is the post-freeze
 * §3.3 extension (2026-07-08) — a quiet-hour skip is now a visible
 * Automation Hub decision, not a silent one. email_sent/email_failed/
 * email_suppressed_quiet_hours are the email-delivery wave's vocabulary,
 * same shape as push (instant alerts only; emailed digests out of scope).
 */
export type AutomationAction =
  | 'notification_created'
  | 'suppressed_by_preference'
  | 'push_sent'
  | 'push_failed'
  | 'push_suppressed_quiet_hours'
  | 'email_sent'
  | 'email_failed'
  | 'email_suppressed_quiet_hours'
  | 'digest_sent';

export interface AutomationLogEntry {
  id: Id;
  kind: AutomationEntryKind;
  action: AutomationAction;
  /** dispatch: the outbox event that triggered the decision. digest: null. */
  eventType: string | null;
  /** digest: the bundled category. dispatch: null. */
  category: string | null;
  /** digest: 'daily' | 'weekly'. dispatch: null. */
  frequency: NotificationFrequency | null;
  windowStart: Timestamp | null;
  windowEnd: Timestamp | null;
  /** The feed row this decision produced, when one exists. */
  activityInboxId: Id | null;
  createdAt: Timestamp;
}

export interface AutomationLogResponse {
  entries: AutomationLogEntry[];
}
