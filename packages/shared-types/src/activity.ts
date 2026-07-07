import type { Id, Timestamp } from './common';

export type ActivityType =
  | 'security'
  | 'system'
  | 'instant_alert' // reserved, unused (see PHASE_6_ARCHITECTURE.md §3.1)
  | 'daily_digest' // Phase 6 — DigestWorker bundle-row marker
  | 'weekly_digest' // Phase 6 — DigestWorker bundle-row marker
  | 'verification' // Phase 6 Wave A (migration 0014 widened the DB enum)
  | 'publishing'; // Phase 6 Wave A (migration 0014 widened the DB enum)

export interface ActivityItem {
  id: Id;
  type: ActivityType;
  title: string;
  body: string | null;
  data: Record<string, unknown>;
  readAt: Timestamp | null;
  createdAt: Timestamp;
}

export interface ActivityInboxResponse {
  items: ActivityItem[];
  unreadCount: number;
}
