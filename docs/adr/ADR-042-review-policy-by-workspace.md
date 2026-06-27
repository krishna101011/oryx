# ADR-042 — Review Policy and Self-Approval Eligibility

**Status:** Accepted — implemented in Phase 5 Wave C
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-039 (draft version control), ADR-033 (analyst override and audit), Phase 2 preferences

---

## 1. Context

A draft moves `in_review → approved` before it can be published. The risk the
review step guards against is the rubber stamp: an analyst approving their *own*
draft with no second pair of eyes. But organisations differ — a solo operator
*must* be able to approve their own work, while a regulated desk wants a hard
second-reviewer rule. The policy needs to be configurable, and it needs to guard
exactly the action that carries the risk and no more.

## 2. Decision

**`verification_strictness` (loose / balanced / strict), the Phase 2 preference,
drives same-account approval eligibility — scoped to the reviewing account.**

The rule lives in one pure function, `_self_approval_allowed`
(`services/drafts/service.py`):

- Approving **someone else's** draft is always allowed.
- Approving your **own** draft is allowed only when the reviewing account is a
  **platform admin**, or its own `verification_strictness` is **`loose`**.
  `balanced` and `strict` (and the absent default, which the caller maps to
  `balanced`) block it.

Two deliberate scoping decisions, verified against the code:

- **Only `approve` carries the self-account restriction.** `reject` and
  `request_changes` carry **no** self-account guard — rejecting or asking for
  changes on your own work has no rubber-stamp risk, so blocking it would only
  add friction. (`reject` and `request_changes` do require a note; `approve` does
  not — Wave C Refinement 1.)
- **Platform admins are exempt regardless of policy.** Verified in
  `approve_draft`: `is_platform_admin` short-circuits the gate.

Eligibility is keyed on the **reviewing** account's own preference (account-scoped
per Phase 2), not the draft author's, because the policy is about the reviewer's
standards for what they are willing to wave through.

## 3. Consequences

### Positive
- A solo workspace (loose) is unblocked; a regulated desk (balanced/strict) gets
  an enforced second reviewer — same code, a preference toggle.
- The guard is exactly as wide as the risk: only `approve`, only self, only when
  policy says so.
- One pure predicate is trivially unit-tested across the full matrix
  (self/other × admin/not × loose/balanced/strict).

### Negative
- "Strict" still trusts that the second approver is genuinely independent — it
  enforces *different account*, not *independent judgment*. Accepted: stronger
  separation-of-duties (role-based reviewer pools) is a later concern, and the
  per-version review records (ADR-039) preserve who approved what for audit.
- Keying on the reviewer's own preference means a lax reviewer can self-approve
  even in a workspace that would prefer otherwise. Accepted as consistent with
  Phase 2's account-scoped preference model; workspace-level enforcement is a
  future extension.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| No self-approval ever | Breaks the solo-operator case entirely; too blunt. |
| Always allow self-approval | Removes the only guard the review step exists to provide. |
| Restrict reject/request-changes too | Adds friction with no risk reduction — neither action can rubber-stamp content live. |
| Key policy on the draft author | The relevant standard is the reviewer's; an author's looseness shouldn't lower a strict reviewer's bar. |
| Hard-code a global rule | Can't serve both solo operators and regulated desks; the preference already exists from Phase 2. |
