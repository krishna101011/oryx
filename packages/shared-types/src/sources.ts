import type { Id, Timestamp } from './common';
import type { Focus } from './preferences';

/** Curated source shipped with the app. */
export interface SourceCatalogEntry {
  key: string;
  name: string;
  url: string;
  focus: Focus;
  editorialConfidence: number; // 0..100
}

/** Per-workspace source selection over the catalog. */
export interface WorkspaceSource {
  workspaceId: Id;
  sourceKey: string;
  enabled: boolean;
  confidenceOverride: number | null; // 0..100
  addedAt: Timestamp;
}

/** User-added source (Phase 3 verifies). */
export interface WorkspaceCustomSource {
  id: Id;
  workspaceId: Id;
  url: string;
  status: 'pending_verification' | 'active' | 'rejected';
  addedAt: Timestamp;
}

export interface UpdateWorkspaceSourceRequest {
  enabled?: boolean;
  confidenceOverride?: number | null;
}
