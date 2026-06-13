/**
 * Phase 4 Wave B — evidence collected for claims.
 *
 * Evidence is created by the verification pipeline (event handler), never
 * by direct API call; the Wave B surface is read-only.
 */
import type { Id, Timestamp } from './common';

export type EvidenceType =
  | 'corroboration'
  | 'contradiction'
  | 'context'
  | 'primary_source'
  | 'secondary_source'
  | 'inference';

export type EvidenceRelationship =
  | 'supports'
  | 'contradicts'
  | 'contextualizes';

export interface Evidence {
  id: Id;
  workspaceId: Id;
  intakeItemId: Id;
  evidenceType: EvidenceType;
  text: string;
  sourceDeleted: boolean;
  createdAt: Timestamp;
}

export interface ClaimEvidenceLink {
  claimId: Id;
  evidenceId: Id;
  relationship: EvidenceRelationship;
  strength: number;
  linkerVersion: number;
}

export interface EvidenceWithLink extends Evidence {
  link: ClaimEvidenceLink;
}
