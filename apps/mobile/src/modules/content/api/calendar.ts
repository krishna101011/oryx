/**
 * Typed wrappers for Phase 5 Wave E calendar endpoints. Workspace-scoped from
 * auth. Request bodies are snake_case (the research convention); the range list
 * passes ISO start/end dates.
 */
import type { ApiResponse, CalendarEntry } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface ScheduleBody {
  draft_id: string;
  target_id: string;
  scheduled_at: string;
}

export const calendarApi = {
  list: (
    startDate: string,
    endDate: string,
  ): Promise<ApiResponse<CalendarEntry[]>> => {
    const q = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    return apiClient().getEnvelope<CalendarEntry[]>(`/calendar?${q.toString()}`);
  },

  schedule: (body: ScheduleBody): Promise<CalendarEntry> =>
    apiClient().post<CalendarEntry, ScheduleBody>('/calendar', body),

  cancel: (entryId: string): Promise<CalendarEntry> =>
    apiClient().delete<CalendarEntry>(`/calendar/${entryId}`),
};
