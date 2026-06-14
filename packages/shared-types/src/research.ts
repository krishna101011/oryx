/**
 * Phase 4 Wave E — research workspaces and packets (the Phase 5 handoff).
 *
 * Analysts curate intelligence objects into workspaces and assemble packets.
 * A packet only reaches 'ready' once its readiness gate passes; Phase 5 is the
 * only consumer that sets consumedAt.
 */
import type { Id, Timestamp } from './common';

export type ResearchPacketStatus = 'assembling' | 'ready' | 'consumed';

export interface ResearchWorkspace {
  id: Id;
  accountId: Id;
  workspaceId: Id;
  name: string;
  description: string | null;
  status: 'active' | 'archived';
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface ResearchWorkspaceItem {
  researchWorkspaceId: Id;
  intelligenceObjectId: Id;
  addedBy: Id;
  note: string | null;
  addedAt: Timestamp;
}

export interface ResearchPacket {
  id: Id;
  researchWorkspaceId: Id;
  workspaceId: Id;
  name: string;
  status: ResearchPacketStatus;
  intelligenceObjectIds: Id[];
  conflictAcknowledgedIds: Id[];
  readyAt: Timestamp | null;
  consumedAt: Timestamp | null;
  createdAt: Timestamp;
}

export interface ReadinessResult {
  isReady: boolean;
  blockers: string[];
}
