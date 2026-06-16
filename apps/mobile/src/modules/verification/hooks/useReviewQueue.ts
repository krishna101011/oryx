import { useQuery } from '@tanstack/react-query';
import type { ReviewQueue } from '@oryx/shared-types';
import { conflictsApi } from '../api/conflicts';

/** The analyst work queue: claims needing review + open conflicts. */
export function useReviewQueue() {
  return useQuery<ReviewQueue>({
    queryKey: ['verification', 'review-queue'],
    queryFn: () => conflictsApi.reviewQueue(),
  });
}
