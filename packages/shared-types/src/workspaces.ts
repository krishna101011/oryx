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

// ============================================================================
// Team/Workspace Rev 2 (docs/TEAM_WORKSPACE_ARCHITECTURE.md) — invites,
// switching, member listing. Backend foundation only — no screen consumes
// these yet.
// ============================================================================

/** GET /v1/workspaces — every real workspace this account actively belongs
 * to (removed_at IS NULL). */
export interface WorkspacesListResponse {
  workspaces: ActiveWorkspace[];
}

/** GET /v1/workspaces/members — real membership rows only, never a removed
 * one. No profile/email join in this foundation wave (a future UI wave can
 * enrich it); accountId is the real, stable identity to key off. */
export interface WorkspaceMemberSummary {
  accountId: Id;
  role: Role;
  joinedAt: Timestamp;
}

/** The invited role is deliberately never 'owner' — ownership is singular
 * per workspace (Workspace.owner_account_id) and isn't granted via invite.
 * A real literal union (not Exclude<Role, 'owner'>) so drift:check actually
 * cross-verifies it against the Python Literal, instead of only noting it
 * as an unchecked Python-only alias. */
export type InviteRole = 'admin' | 'editor' | 'reader';

export interface CreateInviteRequest {
  email: string;
  role: InviteRole;
}

/** Never includes token_hash — the raw token exists only in the invite
 * email, matching the webhook-secret display-once convention. */
export interface WorkspaceInvite {
  id: Id;
  workspaceId: Id;
  invitedEmail: string;
  role: InviteRole;
  invitedBy: Id;
  expiresAt: Timestamp;
  acceptedAt: Timestamp | null;
  revokedAt: Timestamp | null;
  createdAt: Timestamp;
}

export interface AcceptInviteResult {
  workspaceId: Id;
  role: InviteRole;
  joinedAt: Timestamp;
}
