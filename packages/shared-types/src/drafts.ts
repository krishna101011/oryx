/**
 * Phase 5 Wave A — content drafts (the create layer).
 *
 * A draft is generated from a ready research packet by Claude Sonnet, then
 * version-controlled append-only (one new DraftVersion per save/regeneration).
 * Exactly one draft per packet. Content is sourced exclusively from the packet's
 * intelligence objects — never from raw claims or intake items.
 *
 * Request bodies are sent snake_case from the mobile api layer (the research/
 * intake convention); only entity/response shapes live here.
 */
import type { Id, Timestamp } from './common';

export type ContentFormat =
  | 'tweet_thread'
  | 'linkedin_post'
  | 'newsletter_section'
  | 'article'
  | 'report_summary'
  | 'custom';

export type DraftStatus =
  | 'draft'
  | 'in_review'
  | 'changes_requested'
  | 'approved'
  | 'scheduled'
  | 'published'
  | 'rejected'
  | 'archived';

export interface ContentDraft {
  id: Id;
  workspaceId: Id;
  accountId: Id;
  packetId: Id;
  templateId: Id | null;
  format: ContentFormat;
  title: string;
  status: DraftStatus;
  currentVersion: number;
  generationModel: string;
  wordCount: number | null;
  publishedAt: Timestamp | null;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

/** A draft plus its current version's content and provenance — the GET /drafts/{id} shape. */
export interface ContentDraftDetail extends ContentDraft {
  currentContent: string | null;
  currentContentHtml: string | null;
  citationObjectIds: Id[];
}

export interface DraftVersion {
  id: Id;
  draftId: Id;
  versionNumber: number;
  content: string;
  contentHtml: string | null;
  editedBy: Id;
  editNote: string | null;
  wordCount: number | null;
  tokenCount: number | null;
  isAiGenerated: boolean;
  createdAt: Timestamp;
}

export interface DraftCitation {
  draftId: Id;
  intelligenceObjectId: Id;
  addedAt: Timestamp;
}

/** MeResponse.content counts (Phase 5 Wave A surface). */
export interface ContentCounts {
  draftCount: number;
  pendingReviewCount: number;
  scheduledCount: number;
  publishedThisWeek: number;
}
