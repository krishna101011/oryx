import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ConflictDetail, ResolveConflictRequest } from '@anant/shared-types';
import { conflictsApi } from '../api/conflicts';

/** Full conflict detail (both claims, scores, evidence counts). */
export function useConflict(conflictId: string) {
  return useQuery<ConflictDetail>({
    queryKey: ['verification', 'conflict', conflictId],
    queryFn: () => conflictsApi.getConflict(conflictId),
  });
}

/** Resolve a conflict; invalidates the conflict + the review queue. */
export function useResolveConflict(conflictId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ResolveConflictRequest) =>
      conflictsApi.resolveConflict(conflictId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['verification', 'conflict', conflictId] });
      qc.invalidateQueries({ queryKey: ['verification', 'review-queue'] });
    },
  });
}
