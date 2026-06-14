import { useMutation, useQueryClient } from '@tanstack/react-query';
import { reviewApi } from '../api/review';

export function useReviewClaim(claimId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { outcome: string; note: string }) =>
      reviewApi.reviewClaim(claimId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['claims', claimId] });
      qc.invalidateQueries({ queryKey: ['verification', 'review-queue'] });
    },
  });
}

export function useReviewObject(objectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      outcome: 'approved' | 'rejected' | 'flagged';
      note: string;
    }) => reviewApi.reviewObject(objectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['intelligence', 'object', objectId] });
    },
  });
}
