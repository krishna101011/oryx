/**
 * Phase 4 Wave C — verification runs and source credibility.
 *
 * Produced by the deterministic verification engine + scorer (no AI). The
 * Wave C surface is READ-ONLY: runs and credibility evolve from the pipeline,
 * never by direct API call. Mirrors apps/backend/.../verification/schemas.py.
 */
import type { Id, Timestamp } from './common';

export type VerificationOutcome =
  | 'verified'
  | 'unverified'
  | 'contested'
  | 'unverifiable';

export type VerificationStatus = 'pending' | 'running' | 'complete' | 'failed';

/**
 * The six weighted confidence factors (ADR-027). All nullable: a run that
 * could not be scored (unclassified claim) carries null factor scores.
 */
export interface ScoringFactors {
  sourceTrustScore: number | null;
  crossReferenceCountScore: number | null;
  evidenceStrengthScore: number | null;
  recencyScore: number | null;
  claimSpecificityScore: number | null;
  primarySourceAvailable: number | null;
}

export interface VerificationRun {
  id: Id;
  claimId: Id;
  status: VerificationStatus;
  /** null until the run reaches a terminal status. */
  outcome: VerificationOutcome | null;
  /** null for unclassified claims (no epistemic ceiling). */
  confidenceScore: number | null;
  crossReferenceCount: number | null;
  primarySourceFlag: boolean | null;
  factors: ScoringFactors;
  engineVersion: number;
  scoringVersion: number;
  tokensUsed: number;
  startedAt: Timestamp;
  completedAt: Timestamp | null;
}

export interface SourceCredibility {
  workspaceId: Id;
  sourceId: Id;
  accuracyRate: number;
  verifiedClaimCount: number;
  contestedClaimCount: number;
  totalClaimCount: number;
  lastEvaluatedAt: Timestamp | null;
  updatedAt: Timestamp;
}
