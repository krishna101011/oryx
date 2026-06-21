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
};
