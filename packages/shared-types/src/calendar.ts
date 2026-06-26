/**
 * Calendar domain types — Phase 5 Wave E.
 *
 * A CalendarEntry is an analyst's explicit schedule of (draft, target) for a
 * future time. The CalendarScheduler fires 'scheduled' entries when their time
 * arrives, mapping the publish result onto status.
 */

export type CalendarStatus =
  | 'scheduled'
  | 'published'
  | 'cancelled'
  | 'failed';

export interface CalendarEntry {
  id: string;
  workspaceId: string;
  draftId: string;
  targetId: string;
  scheduledAt: string;
  status: CalendarStatus;
  publicationId: string | null;
  createdBy: string;
  createdAt: string;
}

export interface ScheduleDraftRequest {
  draftId: string;
  targetId: string;
  scheduledAt: string;
}
