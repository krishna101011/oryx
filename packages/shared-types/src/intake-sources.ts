/**
 * Phase 3 — operational source records.
 *
 * `intake_sources` is the unified operational table (CR-1).
 * `origin_*` are soft pointers back to the Phase 2 user-facing rows.
 */
import type { Id, Timestamp } from './common';

export type IntakeSourceKind =
  | 'gmail'
  | 'rss'
  | 'webhook'
  | 'api_pull'
  | 'manual';

export type SourceHealth =
  | 'healthy'
  | 'degraded'
  | 'auth_required'
  | 'disabled';

export type OriginKind = 'catalog' | 'custom';

export interface IntakeSource {
  id: Id;
  workspaceId: Id;
  kind: IntakeSourceKind;
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  health: SourceHealth;
  lastSyncedAt: Timestamp | null;
  consecutiveFailures: number;
  originKind: OriginKind;
  originCatalogKey: string | null;
  originCustomId: Id | null;
}

export interface IntakeSourceAuditEntry {
  id: Id;
  intakeSourceId: Id;
  event: string;
  data: Record<string, unknown>;
  createdAt: Timestamp;
}

export interface IntakeStatusSummary {
  total: number;
  byHealth: Record<SourceHealth, number>;
}
