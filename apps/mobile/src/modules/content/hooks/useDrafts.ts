import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ContentDraft,
  ContentDraftDetail,
  DraftReview,
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

// ---- Wave C: review workflow ----

/** The review queue reuses the Wave A filtered list (status=in_review). */
export function useReviewQueue() {
  return useQuery<ContentDraft[]>({
    queryKey: ['content', 'drafts', 'in_review'],
    queryFn: async () => (await draftsApi.listByStatus('in_review')).data,
  });
}

export function useDraftReviews(id: string) {
  return useQuery<DraftReview[]>({
    queryKey: ['content', 'draft', id, 'reviews'],
    queryFn: async () => (await draftsApi.listReviews(id)).data,
  });
}

function useReviewAction<TBody>(
  id: string,
  fn: (id: string, body: TBody) => Promise<ContentDraftDetail>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TBody) => fn(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', id] });
      qc.invalidateQueries({ queryKey: ['content', 'draft', id, 'reviews'] });
      qc.invalidateQueries({ queryKey: ['content', 'drafts'] });
    },
  });
}

export function useSubmitReview(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => draftsApi.submitReview(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['content', 'draft', id] });
      qc.invalidateQueries({ queryKey: ['content', 'drafts'] });
    },
  });
}

export function useApproveDraft(id: string) {
  return useReviewAction<{ note?: string }>(id, draftsApi.approve);
}

export function useRejectDraft(id: string) {
  return useReviewAction<{ note: string }>(id, draftsApi.reject);
}

export function useRequestChanges(id: string) {
  return useReviewAction<{ note: string }>(id, draftsApi.requestChanges);
}
