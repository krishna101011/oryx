/**
 * Typed wrappers for the Phase 4 Wave D conflict + review endpoints.
 *
 * The review queue and conflict reads are workspace-scoped from the auth
 * context. Resolution is a write — note is required (the server rejects an
 * empty note with HTTP 400).
 */
import type {
  ConflictDetail,
  ResolveConflictRequest,
  ReviewQueue,
} from '@anant/shared-types';
import { apiClient } from '../../../lib/api/client';

export interface ResolveConflictResult {
  conflictId: string;
  status: string;
  resolution: string;
  winnerId: string | null;
  loserId: string | null;
  reviewId: string;
}

export const conflictsApi = {
  reviewQueue: (): Promise<ReviewQueue> =>
    apiClient().get<ReviewQueue>('/review/queue'),

  getConflict: (conflictId: string): Promise<ConflictDetail> =>
    apiClient().get<ConflictDetail>(`/conflicts/${conflictId}`),

  resolveConflict: (
    conflictId: string,
    body: ResolveConflictRequest,
  ): Promise<ResolveConflictResult> =>
    apiClient().post<ResolveConflictResult, ResolveConflictRequest>(
      `/conflicts/${conflictId}/resolve`,
      body,
    ),
};
