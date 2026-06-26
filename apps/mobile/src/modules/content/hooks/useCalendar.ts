import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { CalendarEntry } from '@oryx/shared-types';
import { type ScheduleBody, calendarApi } from '../api/calendar';

export function useCalendar(startDate: string, endDate: string) {
  return useQuery<CalendarEntry[]>({
    queryKey: ['content', 'calendar', startDate, endDate],
    queryFn: async () => (await calendarApi.list(startDate, endDate)).data,
  });
}

export function useScheduleDraft(draftId: string) {
  const qc = useQueryClient();
  return useMutation<CalendarEntry, unknown, ScheduleBody>({
    mutationFn: (body: ScheduleBody) => calendarApi.schedule(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', draftId] });
      qc.invalidateQueries({ queryKey: ['content', 'calendar'] });
    },
  });
}

export function useCancelEntry() {
  const qc = useQueryClient();
  return useMutation<CalendarEntry, unknown, string>({
    mutationFn: (entryId: string) => calendarApi.cancel(entryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'calendar'] });
    },
  });
}
