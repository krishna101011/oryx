/**
 * Typed wrappers for the Phase 4 Wave C verification read endpoints (§16.x).
 *
 * Read-only: runs and credibility records are produced by the pipeline. The
 * router scopes everything to the authenticated workspace — no workspace id
 * is ever sent as a parameter.
 */
import type { ApiResponse, Verification } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export const verificationApi = {
  listCredibility: (): Promise<ApiResponse<Verification.SourceCredibility[]>> =>
    apiClient().getEnvelope<Verification.SourceCredibility[]>(
      '/verification/credibility',
    ),

  getCredibility: (sourceId: string): Promise<Verification.SourceCredibility> =>
    apiClient().get<Verification.SourceCredibility>(
      `/verification/credibility/${sourceId}`,
    ),

  runsForClaim: (
    claimId: string,
  ): Promise<ApiResponse<Verification.VerificationRun[]>> =>
    apiClient().getEnvelope<Verification.VerificationRun[]>(
      `/verification/runs?claim_id=${encodeURIComponent(claimId)}`,
    ),

  getRun: (runId: string): Promise<Verification.VerificationRun> =>
    apiClient().get<Verification.VerificationRun>(`/verification/runs/${runId}`),
};
