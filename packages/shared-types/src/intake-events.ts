/**
 * Phase 3 — domain event payloads emitted via the outbox.
 *
 * Payloads carry IDs only — never content. Subscribers (Phase 4 verifier)
 * read full normalized rows from the DB by id.
 */
import type { Id, Timestamp } from './common';

export interface IntakeItemReceived {
  intakeItemId: Id;
  workspaceId: Id;
  intakeSourceId: Id;
  providerName: 'gmail' | 'rss' | 'webhook' | 'api_pull' | 'manual';
  receivedAt: Timestamp;
  fingerprint: string;
  externalId: string;
}
