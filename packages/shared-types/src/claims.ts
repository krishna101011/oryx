/**
 * Phase 4 Wave A — claims extracted from intake items.
 *
 * Claims are created by the verification pipeline (event handler), never
 * by direct API call; the Wave A surface is read-only.
 */
import type { Id, Timestamp } from './common';

export type EpistemicType =
  | 'fact'
  | 'claim'
  | 'rumor'
  | 'speculation'
  | 'opinion'
  | 'unclassified';

export interface Claim {
  id: Id;
  workspaceId: Id;
  intakeItemId: Id;
  text: string;
  subject: string;
  predicate: string;
  object: string | null;
  epistemicType: EpistemicType;
  extractorVersion: number;
  classifierVersion: number | null;
  requiresAnalystReview: boolean;
  supersededBy: Id | null;
  createdAt: Timestamp;
}

/** GET /claims' real response is the generic `ApiResponse<Claim[]>` envelope
 * (flat array in `data`, `Pagination` in `meta.pagination`) — there is
 * deliberately no dedicated response type for this endpoint; a prior
 * `ClaimListResponse { claims, meta }` shape was declared here but never
 * matched what the router actually returns and was never imported anywhere,
 * so it was removed rather than reconciled (same drift class the gen-pydantic
 * unused-export check now catches — see workspaces.ts's ChatMessagesListResponse
 * removal for the precedent). */
