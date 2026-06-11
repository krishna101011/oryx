import type { Id, Timestamp } from './common';

export type ActivityType =
  | 'security'
  | 'system'
  | 'instant_alert' // Phase 4+
  | 'daily_digest' // Phase 6
  | 'weekly_digest'; // Phase 6

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
