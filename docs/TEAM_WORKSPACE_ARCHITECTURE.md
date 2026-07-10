# ORYX — Team/Workspace Architecture

**Scope:** Phase 2 Deepening — NOT one of the 10 numbered phases
**Status:** FROZEN (2026-07-10) — Rev 2, corrected before ever being committed (Rev 1
was never actually saved; two of its sections were built on assumptions
this session's own recon corrected before it could be frozen wrong)
**Depends on:** Phase 2 (WorkspaceMember, capability system, JWT/session
— all already built), the just-shipped email delivery (reused for
invites), the password-reset rewiring fix (should land first, same
email module this reuses)

---

## Revision Note

Rev 1 proposed a session-revocation mechanism for member removal (§6)
based on an assumption that workspace access-cutoff required it. It
doesn't — `get_active_workspace` already re-checks membership on every
request, so removal is already effectively instant at the workspace-
access level. Rev 2 removes that proposed section entirely rather than
build something the real code doesn't need. Rev 1's open question about
reusable transactional email is now answered: reuse the real email
module built for alerts, not auth's old stub.

## 1. What This Actually Is

Not a new authorization system. `WorkspaceMember` (composite PK, role
enum, invited_by, soft-removal), a full `CAPABILITIES` wildcard map, and
`require_capability()` wired onto dozens of live routes already exist and
run on every request today. The real gap is narrow: nobody can be
invited, nobody practically belongs to more than one workspace even
though the schema allows it, and a handful of places assume exactly one
membership per account.

## 2. What NOT to Rebuild

- The role/capability system itself — extend it, don't replace it.
- The `workspace_role` enum — already correct.
- Existing routes' capability checks — already key off the member's row.

## 3. New: Invite Mechanism

New table `workspace_invites`: id, workspace_id, invited_email, role,
token_hash, invited_by, expires_at, accepted_at, revoked_at.

Invite email uses `get_email_provider()` (services/activity/providers/
email/factory.py) with a new "invite" template registered in
rendering.py — the same real module alert delivery already uses, sent as
a one-off transactional call, not routed through NotificationDispatcher's
preference-gated alert flow (an invite isn't a per-category preference).

Endpoints: create invite (capability-gated), view invite by token
(lightly authenticated), accept invite (creates the real
`WorkspaceMember` row), revoke a pending invite.

## 4. New: Workspace Switching

`wsp` is baked into the access token at login; access tokens are
non-revocable within their 15-minute window. Switching workspaces goes
through the existing refresh-token mechanism to mint a new access token
scoped to a different workspace — using the revocation/reissue machinery
that already exists, not inventing a new one.

New endpoints: list an account's workspaces; switch active workspace
(refresh-flow-based reissue).

## 5. Fixing the Confirmed Hardcoded Assumptions

1. `_primary_workspace_id`'s arbitrary `.limit(1)` — becomes an explicit
   "active workspace" concept once switching exists.
2. No list/switch endpoints — built in §4.
3. Workspace rename PATCH has no capability gate — add one regardless of
   anything else here; currently safe only by accident.
4. Digest attribution's workspace_members join (ADR-047's documented
   approximation) — deliberately NOT fixed in this pass; stays a known
   limitation unless real multi-membership usage proves it matters.
5. Signup hardcodes `kind="personal"` — stays that way. Team workspace
   creation is its own explicit action, not a signup branch.

## 6. Capability Convention — a real trap to avoid

`CAPABILITIES["admin"]` enumerates its granted namespaces explicitly
(only `owner` has literal `"*"`). A new `workspace.*` namespace must be
DELIBERATELY added to admin's grant list, or admins silently won't have
it even though the routes exist. Easy to miss; call it out at build time
rather than discover it as a bug report later.

## 7. Explicitly Out of Scope

- Per-seat billing — pending the separate pricing decision.
- Any org hierarchy beyond workspace-has-members-with-roles.
- Fixing the digest-attribution approximation (§5.4).

## 8. Confirm at Build Time

1. Real invite-email template shape, matching rendering.py's existing
   registry pattern exactly.
2. Whether `workspace.read`/`workspace.write`-style capability strings
   need finer granularity (e.g. separate `workspace.invite` vs.
   `workspace.manage`) or two is enough for v1.
