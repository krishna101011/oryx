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
// switching, member listing. Consumed by the web sidebar switcher and
// Settings → Members screen.
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

/** PATCH /v1/workspaces/members/{accountId} — the owner's role is never a
 * valid target (same InviteRole exclusion as invites); ownership transfer
 * is a separate, unbuilt capability. */
export interface ChangeMemberRoleRequest {
  role: InviteRole;
}

/** GET /v1/workspaces/invites — Members-screen gap found while building the
 * UI (not in the frozen Rev 2 doc's endpoint list): create/view/accept/
 * revoke existed, but nothing listed a workspace's own pending invites.
 * Same capability gate as create (workspace.manage). */
export interface WorkspaceInvitesListResponse {
  invites: WorkspaceInvite[];
}

// ============================================================================
// Team nav promotion wave — the Team section's real Activity view (GET
// /v1/workspaces/activity). Not a Postgres enum on the backend (plain Text
// column), so a future event kind is just a new string. 'role_changed' is
// now real — PATCH /v1/workspaces/members/{accountId} (role-change wave)
// emits it with both `role` (the new role) and `previousRole` (what it was),
// following the existing convention that `role` always carries the role
// meaningfully associated with the subject AFTER the event (invited-as,
// joined-as, removed-from). `previousRole` is null for every other event
// kind — only role_changed ever sets it.
// ============================================================================

export type WorkspaceActivityEventType =
  | 'member_invited'
  | 'member_joined'
  | 'member_removed'
  | 'role_changed';

export interface WorkspaceActivityEvent {
  id: Id;
  event: WorkspaceActivityEventType;
  actorAccountId: Id | null;
  subjectAccountId: Id | null;
  subjectEmail: string | null;
  role: string | null;
  previousRole: string | null;
  createdAt: Timestamp;
}

export interface WorkspaceActivityListResponse {
  events: WorkspaceActivityEvent[];
}

// ============================================================================
// Team Chat foundation wave — a single workspace-wide channel (no multi-
// conversation/DM support yet; that's a later, separate scope). Polling-
// friendly: GET /v1/workspaces/messages takes a real cursor (`since`) so a
// second poll returns only messages newer than the last one the client saw,
// not the whole history again — deliberately NOT the unpaginated "latest 50"
// shape WorkspaceAuditLog uses (recon flagged that as unfit for message
// history: no pagination, no edit/delete semantics). No websockets/real-time
// transport — this is HTTP polling only, per the frozen wave scope.
// ============================================================================

/** `body` is null once `deletedAt` is set — soft-delete redacts content from
 * every API response while the row (and its audit trail) stays in the DB;
 * `editedAt` is set on any real edit and left null otherwise. */
export interface ChatMessage {
  id: Id;
  workspaceId: Id;
  senderAccountId: Id;
  body: string | null;
  createdAt: Timestamp;
  editedAt: Timestamp | null;
  deletedAt: Timestamp | null;
}

export interface SendChatMessageRequest {
  body: string;
}

export interface EditChatMessageRequest {
  body: string;
}

/** GET /v1/workspaces/messages — `since` is an opaque cursor from a prior
 * response's `meta.pagination.nextCursor` (same Phase 1 cursor envelope
 * `claims.ts` uses). Omitting `since` returns the latest page of history;
 * passing the last cursor a client saw returns only messages strictly after
 * it — the real "don't refetch the whole history on every poll" behavior.
 * The real wire response is the generic `ApiResponse<ChatMessage[]>`
 * envelope (flat array in `data`, `Pagination` in `meta.pagination`) — there
 * is deliberately no dedicated response type for this endpoint; a prior
 * `ChatMessagesListResponse { messages, meta }` shape was declared here but
 * never matched what the router actually returns and was never imported
 * anywhere, so it was removed rather than reconciled. */

/** One row per (workspace, account) — the minimal marker an unread indicator
 * needs. `lastReadMessageId`/`lastReadAt` are both null until the account
 * marks anything read at least once. */
export interface ChatReadMarker {
  workspaceId: Id;
  accountId: Id;
  lastReadMessageId: Id | null;
  lastReadAt: Timestamp | null;
}

export interface MarkChatReadRequest {
  messageId: Id;
}
