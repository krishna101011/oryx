/**
 * Phase 4 Wave E — intelligence objects (the fan-in of verified claims).
 *
 * Objects are composed by the pipeline (verification.claim.verified →
 * composition); this surface is read-only. headline is intake-derived plain
 * text and keyFacts is structured extraction — never AI prose.
 */
import type { EpistemicType } from './claims';
import type { Id, Timestamp } from './common';

export type IntelligenceStatus =
  | 'unverified'
  | 'verified'
  | 'contested'
  | 'analyst_approved'
  | 'analyst_rejected';

export interface IntelligenceObject {
  id: Id;
  workspaceId: Id;
  intakeItemId: Id;
  epistemicType: EpistemicType;
  confidenceScore: number | null;
  verificationStatus: IntelligenceStatus;
  claimIds: Id[];
  conflictIds: Id[];
  keyFacts: Record<string, unknown>;
  headline: string;
  scoringVersion: number;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

/** GET /v1/intelligence/objects/{id}/stale — read-only version check. */
export interface StaleCheck {
  isStale: boolean;
  currentVersion: number;
  objectVersion: number;
}
