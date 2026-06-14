/** Analyst override + object review writes (Wave D/E). note is required. */
import { apiClient } from '../../../lib/api/client';

export interface ReviewResult {
  reviewId: string;
  outcome: string;
}

export const reviewApi = {
  reviewClaim: (
    claimId: string,
    body: { outcome: string; note: string },
  ): Promise<ReviewResult> =>
    apiClient().post<ReviewResult, typeof body>(
      `/review/claims/${claimId}`,
      body,
    ),

  reviewObject: (
    objectId: string,
    body: { outcome: 'approved' | 'rejected' | 'flagged'; note: string },
  ): Promise<ReviewResult> =>
    apiClient().post<ReviewResult, typeof body>(
      `/review/objects/${objectId}`,
      body,
    ),
};
