/**
 * Phase 5 Wave C — draft review workflow.
 *
 * A draft moves through submit → review → approve before Wave D's publishing
 * engine may touch it. Each review action appends one DraftReview audit row.
 * `note` is required for 'rejected' / 'changes_requested' (enforced at the API
 * layer, HTTP 400) and optional for 'approved'. Self-approval is gated by the
 * reviewing account's verification_strictness preference (§15.3).
 *
 * Request bodies are sent snake_case from the mobile api layer (the research/
 * intake convention); only entity/response shapes live here.
 */
import type { Id, Timestamp } from './common';

export type ReviewOutcome = 'approved' | 'rejected' | 'changes_requested';

export interface DraftReview {
  id: Id;
  draftId: Id;
  versionNumber: number;
  accountId: Id;
  outcome: ReviewOutcome;
  note: string | null;
  createdAt: Timestamp;
}

export interface ApproveDraftRequest {
  note?: string;
}

export interface RejectDraftRequest {
  note: string;
}

export interface RequestChangesRequest {
  note: string;
}
