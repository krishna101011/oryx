/**
 * Typed wrappers for Phase 5 Wave D publishing endpoints. Workspace-scoped from
 * auth. Credentials are write-only — they are sent on create and never returned.
 */
import type {
  ApiResponse,
  Publication,
  PublicationProvenance,
  PublishChannel,
  PublishTarget,
  PublishTargetResult,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface CreateTargetBody {
  name: string;
  channel: PublishChannel;
  credentials: Record<string, unknown>;
  config: Record<string, unknown>;
}

export const targetsApi = {
  list: (): Promise<ApiResponse<PublishTarget[]>> =>
    apiClient().getEnvelope<PublishTarget[]>('/targets'),

  get: (id: string): Promise<PublishTarget> =>
    apiClient().get<PublishTarget>(`/targets/${id}`),

  create: (body: CreateTargetBody): Promise<PublishTarget> =>
    apiClient().post<PublishTarget, CreateTargetBody>('/targets', body),

  remove: (id: string): Promise<{ deleted: boolean }> =>
    apiClient().delete<{ deleted: boolean }>(`/targets/${id}`),

  healthCheck: (id: string): Promise<{ ok: boolean }> =>
    apiClient().post<{ ok: boolean }>(`/targets/${id}/health-check`),
};

export const publishingApi = {
  publish: (
    draftId: string,
    targetIds: string[],
  ): Promise<PublishTargetResult[]> =>
    apiClient().post<PublishTargetResult[], { target_ids: string[] }>(
      `/drafts/${draftId}/publish`,
      { target_ids: targetIds },
    ),

  publications: (params?: {
    status?: string;
    draftId?: string;
  }): Promise<ApiResponse<Publication[]>> => {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.draftId) q.set('draft_id', params.draftId);
    const qs = q.toString();
    return apiClient().getEnvelope<Publication[]>(
      `/publications${qs ? `?${qs}` : ''}`,
    );
  },

  /** Snapshotted provenance ("show your work") for one publication. */
  provenance: (
    publicationId: string,
  ): Promise<ApiResponse<PublicationProvenance>> =>
    apiClient().getEnvelope<PublicationProvenance>(
      `/publications/${publicationId}/provenance`,
    ),
};
