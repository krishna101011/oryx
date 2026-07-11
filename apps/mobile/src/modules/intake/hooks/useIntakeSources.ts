import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { IntakeSource, IntakeStatusSummary, RecentIntakeItem } from '@oryx/shared-types';
import {
  intakeApi,
  type CreateSourceBody,
  type PatchSourceBody,
} from '../api/intake';

const SOURCES_KEY = ['intake', 'sources'];

export function useIntakeSources() {
  return useQuery<IntakeSource[]>({
    queryKey: SOURCES_KEY,
    queryFn: async () => (await intakeApi.listSources()).data,
    staleTime: 30 * 1000,
  });
}

export function useIntakeStatus() {
  return useQuery<IntakeStatusSummary>({
    // Under the ['intake'] prefix so every source mutation's
    // invalidateQueries({ queryKey: ['intake'] }) refreshes this count too.
    queryKey: ['intake', 'status'],
    queryFn: () => intakeApi.status(),
    staleTime: 30 * 1000,
  });
}

export function useRecentIntakeItems(limit = 10) {
  return useQuery<RecentIntakeItem[]>({
    // Under the ['intake'] prefix for the same reason as status above.
    queryKey: ['intake', 'recent-items', limit],
    queryFn: async () => (await intakeApi.recentItems(limit)).data,
    staleTime: 30 * 1000,
  });
}

export function useIntakeSource(sourceId: string) {
  return useQuery<IntakeSource>({
    queryKey: [...SOURCES_KEY, sourceId],
    queryFn: () => intakeApi.getSource(sourceId),
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSourceBody) => intakeApi.createSource(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  });
}

export function usePatchSource(sourceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PatchSourceBody) => intakeApi.patchSource(sourceId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  });
}

export function useDeleteSource(sourceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => intakeApi.deleteSource(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  });
}

export function useTriggerSync(sourceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => intakeApi.triggerSync(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  });
}
