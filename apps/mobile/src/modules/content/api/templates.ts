/**
 * Typed wrappers for Phase 5 Wave B template endpoints. Workspace-scoped from auth.
 */
import type {
  ApiResponse,
  ContentTemplate,
  CreateTemplateRequest,
  UpdateTemplateRequest,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export const templatesApi = {
  list: (format?: string): Promise<ApiResponse<ContentTemplate[]>> => {
    const params = format ? `?format=${encodeURIComponent(format)}` : '';
    return apiClient().getEnvelope<ContentTemplate[]>(`/templates${params}`);
  },

  get: (id: string): Promise<ContentTemplate> =>
    apiClient().get<ContentTemplate>(`/templates/${id}`),

  create: (body: CreateTemplateRequest): Promise<ContentTemplate> =>
    apiClient().post<ContentTemplate, CreateTemplateRequest>('/templates', body),

  update: (id: string, body: UpdateTemplateRequest): Promise<ContentTemplate> =>
    apiClient().patch<ContentTemplate, UpdateTemplateRequest>(
      `/templates/${id}`,
      body,
    ),

  delete: (id: string): Promise<{ deleted: string }> =>
    apiClient().delete<{ deleted: string }>(`/templates/${id}`),
};
