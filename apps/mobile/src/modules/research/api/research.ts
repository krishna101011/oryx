/**
 * Typed wrappers for Phase 4 Wave E research endpoints. All workspace-scoped
 * from auth. mark-ready returns HTTP 409 (with a blocker list) when the
 * readiness gate fails.
 */
import type {
  ApiResponse,
  ReadinessResult,
  ResearchPacket,
  ResearchWorkspace,
} from '@anant/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface WorkspaceDetail extends ResearchWorkspace {
  itemCount: number;
}

export interface ResearchItemView {
  researchWorkspaceId: string;
  intelligenceObjectId: string;
  addedBy: string;
  note: string | null;
  addedAt: string;
  object: {
    id: string;
    headline: string;
    epistemicType: string;
    confidenceScore: number | null;
    verificationStatus: string;
  } | null;
}

export const researchApi = {
  listWorkspaces: (): Promise<ApiResponse<ResearchWorkspace[]>> =>
    apiClient().getEnvelope<ResearchWorkspace[]>('/research/workspaces'),

  getWorkspace: (id: string): Promise<WorkspaceDetail> =>
    apiClient().get<WorkspaceDetail>(`/research/workspaces/${id}`),

  createWorkspace: (body: {
    name: string;
    description?: string | null;
  }): Promise<ResearchWorkspace> =>
    apiClient().post<ResearchWorkspace, typeof body>(
      '/research/workspaces',
      body,
    ),

  listItems: (id: string): Promise<ApiResponse<ResearchItemView[]>> =>
    apiClient().getEnvelope<ResearchItemView[]>(
      `/research/workspaces/${id}/items`,
    ),

  addItem: (
    id: string,
    body: { intelligence_object_id: string; note?: string | null },
  ): Promise<unknown> =>
    apiClient().post(`/research/workspaces/${id}/items`, body),

  createPacket: (body: {
    research_workspace_id: string;
    name: string;
    intelligence_object_ids: string[];
  }): Promise<ResearchPacket> =>
    apiClient().post<ResearchPacket, typeof body>('/research/packets', body),

  listPacketsForWorkspace: (): Promise<ApiResponse<ResearchPacket[]>> =>
    apiClient().getEnvelope<ResearchPacket[]>('/research/packets'),

  getPacket: (id: string): Promise<ResearchPacket> =>
    apiClient().get<ResearchPacket>(`/research/packets/${id}`),

  getReadiness: (id: string): Promise<ReadinessResult> =>
    apiClient().get<ReadinessResult>(`/research/packets/${id}/readiness`),

  markReady: (id: string): Promise<ResearchPacket> =>
    apiClient().post<ResearchPacket>(`/research/packets/${id}/ready`),

  acknowledgeConflict: (
    id: string,
    body: { intelligence_object_id: string },
  ): Promise<unknown> =>
    apiClient().post(`/research/packets/${id}/acknowledge-conflict`, body),
};
