import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ContentDraft,
  ContentDraftDetail,
  DraftVersion,
} from '@oryx/shared-types';
import { type GenerateBody, draftsApi } from '../api/drafts';

export function useDraftList() {
  return useQuery<ContentDraft[]>({
    queryKey: ['content', 'drafts'],
    queryFn: async () => (await draftsApi.list()).data,
  });
}

export function useDraft(id: string) {
  return useQuery<ContentDraftDetail>({
    queryKey: ['content', 'draft', id],
    queryFn: () => draftsApi.get(id),
  });
}

export function useDraftVersions(id: string) {
  return useQuery<DraftVersion[]>({
    queryKey: ['content', 'draft', id, 'versions'],
    queryFn: async () => (await draftsApi.listVersions(id)).data,
  });
}

export function useGenerateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerateBody) => draftsApi.generate(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['content', 'drafts'] }),
  });
}

export function useRegenerateDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { instructions?: string | null }) =>
      draftsApi.regenerate(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', id] });
      qc.invalidateQueries({ queryKey: ['content', 'draft', id, 'versions'] });
    },
  });
}

export function useSaveVersion(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      content: string;
      content_html?: string | null;
      edit_note?: string | null;
    }) => draftsApi.saveVersion(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', id] });
      qc.invalidateQueries({ queryKey: ['content', 'draft', id, 'versions'] });
      qc.invalidateQueries({ queryKey: ['content', 'drafts'] });
    },
  });
}

export function useSwitchFormat(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { format: ContentDraftDetail['format']; template_id?: string | null }) =>
      draftsApi.switchFormat(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', id] });
      qc.invalidateQueries({ queryKey: ['content', 'draft', id, 'versions'] });
      qc.invalidateQueries({ queryKey: ['content', 'drafts'] });
    },
  });
}
