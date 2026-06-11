/**
 * Phase 3 — intake item types.
 *
 * Mobile and integration consumers see `IntakeItem` (IDs + counts only).
 * The full raw payload is internal-only and lives in the backend models.
 */
import type { Id, Timestamp } from './common';

export interface IntakeItem {
  id: Id;
  workspaceId: Id;
  intakeSourceId: Id;
  providerName: string;
  externalId: string;
  receivedAt: Timestamp;
  fingerprint: string;
}

export interface NormalizedItemView {
  intakeItemId: Id;
  senderDomain: string | null;
  senderLabel: string | null;
  subject: string | null;
  linkCount: number;
  normalizedAt: Timestamp;
  normalizerVersion: number;
}

// ---- Manual ingest (CR-8, platform admin only) ----

/** Body for POST /admin/intake/manual_ingest. snake_case per the intake
 *  router's body convention. */
export interface ManualIngestRequest {
  workspace_id: Id;
  title: string;
  url?: string | null;
  body_text?: string | null;
  sender?: string | null;
}

export interface ManualIngestResponse {
  outcome: 'inserted' | 'skipped_provider_key' | 'skipped_fingerprint';
  intakeItemId: Id | null;
  fingerprint: string;
}
