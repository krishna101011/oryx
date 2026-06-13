/**
 * Phase 4 Wave D — conflict detection, resolution, and analyst review.
 *
 * Conflict records are produced by the pipeline (verification.claim.verified →
 * detection). Resolution and analyst review flow through the write endpoints;
 * the rest of this surface is read-only.
 */
import type { Claim } from './claims';
import type { Id, Timestamp } from './common';

export type ConflictType =
  | 'direct_contradiction'
  | 'factual_disagreement'
  | 'temporal_inconsistency'
  | 'scope_difference';

export type ConflictStatus =
  | 'open'
  | 'resolved_a_wins'
  | 'resolved_b_wins'
  | 'resolved_inconclusive'
  | 'resolved_system'
  | 'analyst_reviewed';

export type ConflictResolver = 'system' | 'analyst';

export type AnalystEntityType = 'claim' | 'intelligence_object' | 'conflict';

export interface ConflictRecord {
  id: Id;
  workspaceId: Id;
  claimAId: Id;
  claimBId: Id;
  conflictType: ConflictType;
  severity: number;
  status: ConflictStatus;
  resolutionNote: string | null;
  resolvedByKind: ConflictResolver | null;
  resolvedAt: Timestamp | null;
  createdAt: Timestamp;
}

export interface AnalystReview {
  id: Id;
  accountId: Id;
  workspaceId: Id;
  entityType: AnalystEntityType;
  entityId: Id;
  outcome: string;
  note: string;
  createdAt: Timestamp;
}

/**
 * GET /v1/conflicts/{id}. Carries both claims plus the data the review screen
 * needs: each claim's latest confidence score and its evidence-type counts.
 */
export interface ConflictDetail extends ConflictRecord {
  claimA: Claim;
  claimB: Claim;
  claimAScore: number | null;
  claimBScore: number | null;
  claimAEvidenceCounts: Record<string, number>;
  claimBEvidenceCounts: Record<string, number>;
}

export interface ReviewQueue {
  pendingClaims: Claim[];
  openConflicts: ConflictRecord[];
}

/** POST /v1/conflicts/{id}/resolve */
export interface ResolveConflictRequest {
  outcome: 'a_wins' | 'b_wins' | 'inconclusive';
  note: string;
}
