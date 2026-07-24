import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  IntakeSource,
  IntakeStatusSummary,
  RecentIntakeItem,
  SourceCatalogEntry,
} from '@oryx/shared-types';
import {
  intakeApi,
  type CreateSourceBody,
  type PatchSourceBody,
} from '../api/intake';
import type { ToggleAction } from '../catalogPicker';

const SOURCES_KEY = ['intake', 'sources'];
const CATALOG_KEY = ['sources', 'catalog'];

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

/** The curated source_catalog list — same query key both the Settings and
 * onboarding pickers used to declare inline; centralized here so they can
 * never diverge in cache shape. */
export function useSourceCatalog() {
  return useQuery<SourceCatalogEntry[]>({
    queryKey: CATALOG_KEY,
    queryFn: () => intakeApi.getCatalog(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Enabling/disabling a catalog picker tile always goes through the real
 * origin_kind='catalog' intake_sources path (POST to create the first real
 * row, PATCH to flip `enabled` on one that already exists) — never the
 * WorkspaceSource toggle, which has no real pipeline effect.
 */
export function useToggleCatalogSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (action: ToggleAction) =>
      action.kind === 'create'
        ? intakeApi.createSource({
            name: '',
            kind: 'rss',
            origin_kind: 'catalog',
            origin_catalog_key: action.catalogKey,
            config: {},
          })
        : intakeApi.patchSource(action.sourceId, { enabled: action.enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['intake'] }),
  });
}
