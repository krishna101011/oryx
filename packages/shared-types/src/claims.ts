/**
 * Phase 4 Wave A — claims extracted from intake items.
 *
 * Claims are created by the verification pipeline (event handler), never
 * by direct API call; the Wave A surface is read-only.
 */
import type { Id, Pagination, Timestamp } from './common';

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

/** List responses use the Phase 1 envelope; `meta.pagination` carries the
 *  cursor pair (the spec's `PaginationMeta` maps onto `Pagination`). */
export interface ClaimListResponse {
  claims: Claim[];
  meta: { pagination: Pagination };
}
