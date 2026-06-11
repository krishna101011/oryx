import type { Id, Timestamp } from './common';

export type WorkspaceKind = 'personal' | 'team';
export type WorkspacePlan = 'free' | 'pro' | 'enterprise';
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
