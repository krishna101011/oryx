/**
 * Typed wrappers for Phase 5 Wave A draft endpoints. All workspace-scoped from
 * auth. Generation runs on Claude Sonnet, constrained to the packet's
 * intelligence objects. Request bodies are snake_case (the research convention).
 */
import type {
  ApiResponse,
  ContentDraft,
  ContentDraftDetail,
  ContentFormat,
  DraftReview,
  DraftStatus,
  DraftVersion,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface GenerateBody {
  packet_id: string;
  format: ContentFormat;
  template_id?: string | null;
  instructions?: string | null;
}

export const draftsApi = {
  list: (): Promise<ApiResponse<ContentDraft[]>> =>
    apiClient().getEnvelope<ContentDraft[]>('/drafts'),

  // Wave C: the review queue reuses the Wave A filtered-list endpoint —
  // there is deliberately no dedicated review-queue endpoint.
  listByStatus: (status: DraftStatus): Promise<ApiResponse<ContentDraft[]>> =>
    apiClient().getEnvelope<ContentDraft[]>(`/drafts?status=${status}`),

  get: (id: string): Promise<ContentDraftDetail> =>
    apiClient().get<ContentDraftDetail>(`/drafts/${id}`),

  listVersions: (id: string): Promise<ApiResponse<DraftVersion[]>> =>
    apiClient().getEnvelope<DraftVersion[]>(`/drafts/${id}/versions`),

  generate: (body: GenerateBody): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, GenerateBody>('/drafts/generate', body),

  regenerate: (
    id: string,
    body: { instructions?: string | null },
  ): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, typeof body>(
      `/drafts/${id}/regenerate`,
      body,
    ),

  saveVersion: (
    id: string,
    body: {
      content: string;
      content_html?: string | null;
      edit_note?: string | null;
    },
  ): Promise<ContentDraftDetail> =>
    apiClient().put<ContentDraftDetail, typeof body>(`/drafts/${id}/version`, body),

  switchFormat: (
    id: string,
    body: { format: ContentFormat; template_id?: string | null },
  ): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, typeof body>(
      `/drafts/${id}/switch-format`,
      body,
    ),

  // ---- Wave C: review workflow ----

  submitReview: (id: string): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail>(`/drafts/${id}/submit-review`),

  approve: (id: string, body: { note?: string }): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, typeof body>(`/drafts/${id}/approve`, body),

  reject: (id: string, body: { note: string }): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, typeof body>(`/drafts/${id}/reject`, body),

  requestChanges: (
    id: string,
    body: { note: string },
  ): Promise<ContentDraftDetail> =>
    apiClient().post<ContentDraftDetail, typeof body>(
      `/drafts/${id}/request-changes`,
      body,
    ),

  listReviews: (id: string): Promise<ApiResponse<DraftReview[]>> =>
    apiClient().getEnvelope<DraftReview[]>(`/drafts/${id}/reviews`),
};
