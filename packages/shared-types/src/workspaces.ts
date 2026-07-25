import type { Id, Timestamp } from './common';

export type WorkspaceKind = 'personal' | 'team';
// Billing foundation wave: widened from ('free'|'pro'|'enterprise') to the
// real 4-tier model. See apps/backend/alembic/versions/0029_billing_foundation.py
// for the free/pro/enterprise -> glimpse/focus/vision data mapping.
export type WorkspacePlan = 'glimpse' | 'focus' | 'clarity' | 'vision';
export type Role = 'owner' | 'admin' | 'editor' | 'reader';

export interface Workspace {
  id: Id;
  name: string;
  kind: WorkspaceKind;
  plan: WorkspacePlan;
  createdAt: Timestamp;
}

export interface WorkspaceMember {
  workspaceId: Id;
  accountId: Id;
  role: Role;
  joinedAt: Timestamp;
}

/** Shape used in /v1/auth/me's `workspace` field. */
export interface ActiveWorkspace {
  id: Id;
  name: string;
  kind: WorkspaceKind;
  role: Role;
}
