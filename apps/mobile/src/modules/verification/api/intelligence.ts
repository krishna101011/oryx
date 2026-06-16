/**
 * Typed wrappers for Phase 4 Wave E intelligence reads + the claim/evidence
 * detail reads the verification screens need. All workspace-scoped from auth.
 */
import type {
  ApiResponse,
  Claim,
  EvidenceWithLink,
  IntelligenceObject,
  StaleCheck,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface ObjectFilters {
  status?: string;
  epistemicType?: string;
  minScore?: number;
  search?: string;
}

function toQuery(f: ObjectFilters): string {
  const parts: string[] = [];
  if (f.status) parts.push(`status=${encodeURIComponent(f.status)}`);
  if (f.epistemicType)
    parts.push(`epistemic_type=${encodeURIComponent(f.epistemicType)}`);
  if (f.minScore !== undefined) parts.push(`min_score=${f.minScore}`);
  if (f.search) parts.push(`search=${encodeURIComponent(f.search)}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export const intelligenceApi = {
  listObjects: (
    f: ObjectFilters = {},
  ): Promise<ApiResponse<IntelligenceObject[]>> =>
    apiClient().getEnvelope<IntelligenceObject[]>(
      `/intelligence/objects${toQuery(f)}`,
    ),

  getObject: (id: string): Promise<IntelligenceObject> =>
    apiClient().get<IntelligenceObject>(`/intelligence/objects/${id}`),

  getStale: (id: string): Promise<StaleCheck> =>
    apiClient().get<StaleCheck>(`/intelligence/objects/${id}/stale`),

  getClaim: (id: string): Promise<Claim> =>
    apiClient().get<Claim>(`/claims/${id}`),

  listEvidence: (claimId: string): Promise<ApiResponse<EvidenceWithLink[]>> =>
    apiClient().getEnvelope<EvidenceWithLink[]>(
      `/evidence?claim_id=${encodeURIComponent(claimId)}`,
    ),
};
