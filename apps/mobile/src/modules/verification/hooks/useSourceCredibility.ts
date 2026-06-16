import { useQuery } from '@tanstack/react-query';
import type { Verification } from '@oryx/shared-types';
import { AppApiError } from '../../../lib/errors';
import { verificationApi } from '../api/verification';

/**
 * Per-source credibility record. A source that has not yet produced a
 * verified claim has no record — the endpoint 404s, which we surface as a
 * resolved `null` so the screen can render an empty state rather than an error.
 */
export function useSourceCredibility(sourceId: string) {
  return useQuery<Verification.SourceCredibility | null>({
    queryKey: ['verification', 'credibility', sourceId],
    queryFn: async () => {
      try {
        return await verificationApi.getCredibility(sourceId);
      } catch (err) {
        if (err instanceof AppApiError && err.code === 'NOT_FOUND') return null;
        throw err;
      }
    },
  });
}
