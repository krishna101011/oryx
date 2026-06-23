import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  Publication,
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
