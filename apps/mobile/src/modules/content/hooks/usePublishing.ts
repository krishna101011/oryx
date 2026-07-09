import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  Publication,
  PublicationProvenance,
  PublishTarget,
  PublishTargetResult,
} from '@oryx/shared-types';
import {
  type CreateTargetBody,
  publishingApi,
  targetsApi,
} from '../api/publishing';

export function useTargets() {
  return useQuery<PublishTarget[]>({
    queryKey: ['publishing', 'targets'],
    queryFn: async () => (await targetsApi.list()).data,
  });
}

export function useCreateTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateTargetBody) => targetsApi.create(body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['publishing', 'targets'] }),
  });
}

export function useDeleteTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => targetsApi.remove(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['publishing', 'targets'] }),
  });
}

export function useHealthCheck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => targetsApi.healthCheck(id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['publishing', 'targets'] }),
  });
}

export function usePublishDraft(draftId: string) {
  const qc = useQueryClient();
  return useMutation<PublishTargetResult[], unknown, string[]>({
    mutationFn: (targetIds: string[]) =>
      publishingApi.publish(draftId, targetIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', draftId] });
      qc.invalidateQueries({ queryKey: ['publishing', 'publications'] });
    },
  });
}

export function usePublications(params?: { status?: string; draftId?: string }) {
  return useQuery<Publication[]>({
    queryKey: ['publishing', 'publications', params ?? {}],
    queryFn: async () => (await publishingApi.publications(params)).data,
  });
}

/**
 * Snapshotted provenance for one publication — fetched lazily (enabled only
 * once the "show your work" section is expanded). The payload is immutable
 * server-side, so a long staleTime is correct, not a caching shortcut.
 */
export function usePublicationProvenance(
  publicationId: string,
  enabled: boolean,
) {
  return useQuery<PublicationProvenance>({
    queryKey: ['publishing', 'provenance', publicationId],
    queryFn: async () =>
      (await publishingApi.provenance(publicationId)).data,
    enabled,
    staleTime: Infinity,
  });
}
