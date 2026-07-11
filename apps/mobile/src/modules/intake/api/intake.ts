/**
 * Typed wrappers for the Phase 3 intake endpoints (§14.2).
 *
 * Note: the intake routers take snake_case request bodies; responses are
 * camelCase per the shared-types contract.
 */
import type {
  ApiResponse,
  IntakeSource,
  IntakeSourceAuditEntry,
  IntakeStatusSummary,
  ManualIngestRequest,
  ManualIngestResponse,
  RecentIntakeItem,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface CreateSourceBody {
  name: string;
  kind: 'rss' | 'gmail' | 'webhook' | 'api_pull';
  origin_kind: 'catalog' | 'custom';
  origin_catalog_key?: string | null;
  origin_custom_id?: string | null;
  config: Record<string, unknown>;
}

export interface PatchSourceBody {
  name?: string;
  enabled?: boolean;
  config?: Record<string, unknown>;
}

export const intakeApi = {
  listSources: (): Promise<ApiResponse<IntakeSource[]>> =>
    apiClient().getEnvelope<IntakeSource[]>('/intake/sources'),

  getSource: (id: string): Promise<IntakeSource> =>
    apiClient().get<IntakeSource>(`/intake/sources/${id}`),

  createSource: (body: CreateSourceBody): Promise<IntakeSource> =>
    apiClient().post<IntakeSource, CreateSourceBody>('/intake/sources', body),

  patchSource: (id: string, body: PatchSourceBody): Promise<IntakeSource> =>
    apiClient().patch<IntakeSource, PatchSourceBody>(`/intake/sources/${id}`, body),

  deleteSource: (id: string): Promise<{ ok: boolean }> =>
    apiClient().delete<{ ok: boolean }>(`/intake/sources/${id}`),

  triggerSync: (id: string): Promise<{ queued: boolean }> =>
    apiClient().post<{ queued: boolean }>(`/intake/sources/${id}/sync`),

  status: (): Promise<IntakeStatusSummary> =>
    apiClient().get<IntakeStatusSummary>('/intake/status'),

  recentItems: (limit = 10): Promise<ApiResponse<RecentIntakeItem[]>> =>
    apiClient().getEnvelope<RecentIntakeItem[]>(`/intake/items/recent?limit=${limit}`),

  audit: (
    sourceId: string,
    cursor?: string | null,
  ): Promise<ApiResponse<IntakeSourceAuditEntry[]>> =>
    apiClient().getEnvelope<IntakeSourceAuditEntry[]>(
      `/intake/sources/${sourceId}/audit${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`,
    ),

  startGmailOauth: (): Promise<{ intakeSourceId: string; authUrl: string }> =>
    apiClient().post<{ intakeSourceId: string; authUrl: string }>(
      '/intake/oauth/gmail/start',
    ),

  manualIngest: (body: ManualIngestRequest): Promise<ManualIngestResponse> =>
    apiClient().post<ManualIngestResponse, ManualIngestRequest>(
      '/admin/intake/manual_ingest',
      body,
    ),
};
