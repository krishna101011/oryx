/**
 * Publishing domain types — Phase 5 Wave D.
 *
 * PublishTarget deliberately has NO credentials field: channel credentials are
 * write-only (encrypted at rest, never returned by any endpoint — §13.2).
 */

export type PublishChannel =
  | 'twitter_x'
  | 'linkedin'
  | 'email_newsletter'
  | 'notion'
  | 'webhook'
  | 'export';

export type PublicationStatus =
  | 'pending'
  | 'delivering'
  | 'delivered'
  | 'failed'
  | 'cancelled';

export interface PublishTarget {
  id: string;
  workspaceId: string;
  name: string;
  channel: PublishChannel;
  config: Record<string, unknown>;
  isActive: boolean;
  lastHealthAt: string | null;
  lastHealthOk: boolean | null;
  createdAt: string;
  // deliberately NO credentials field — never exposed
}

export interface Publication {
  id: string;
  draftId: string;
  versionNumber: number;
  targetId: string;
  workspaceId: string;
  status: PublicationStatus;
  externalId: string | null;
  externalUrl: string | null;
  errorMessage: string | null;
  publishedAt: string | null;
  createdAt: string;
}

export interface PublishRequest {
  targetIds: string[];
}

/** Per-target outcome returned by POST /v1/drafts/{id}/publish. */
export interface PublishTargetResult {
  targetId: string;
  publicationId: string | null;
  status: 'delivered' | 'failed' | 'pending' | 'skipped';
  externalId: string | null;
  externalUrl: string | null;
  errorMessage: string | null;
}
