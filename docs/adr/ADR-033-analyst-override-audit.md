# ADR-033 — Analyst Override and Audit

**Status:** Accepted
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-032 (engine versioning), ADR-014 (event architecture)

---

## 1. Context

Phase 4's defining constraint is epistemic integrity, and one of its
principles is: *the system never prevents a human from overriding its output,
and every override is logged with a mandatory note.* An analyst must be able
to verify a claim the engine left unverified, reject an object the score
favored, or resolve a conflict the auto-resolver escalated — and every such
act must be reconstructable later, for both quality review and legal
compliance.

The risk is the easy, wrong design: mutate the original record in place. That
destroys the system's own judgment, leaving no way to ask "what did the
engine think before the human intervened, and why did the human disagree?"

## 2. Decision

**Overrides are non-destructive.** An analyst action writes an
`analyst_reviews` row — `(account_id, workspace_id, entity_type, entity_id,
outcome, note)` — and **never mutates** the underlying claim, intelligence
object, or conflict record. The original system decision (the
`verification_runs` row, the object's computed score) stays intact; the
review is an overlay, not an edit.

**The note is mandatory.** `analyst_reviews.note` is enforced non-empty *at
the API layer* (empty string rejected). An override without a stated reason
is not an override worth auditing.

**Every Phase 4 decision — system and analyst — lands in
`verification_audit_log`**: append-only, `(workspace_id, account_id, event,
entity_type, entity_id, data)`, 7-year retention, `account_id` NULL for
system actions. This is a *separate* table from `auth_audit_log` (ADR
precedent: different schema, query pattern, and retention; the two must not
be operationally coupled). All Phase 4 services write it through the review
module's repository.

**Supersession, not deletion.** When conflict resolution retires a claim, its
`superseded_by` is set — the losing claim persists, fully auditable, with a
pointer to its successor. Nothing in the verification chain is ever hard-
deleted except by the workspace-delete cascade (CR-6).

## 3. Consequences

### Positive
- Complete, reconstructable decision trail: system judgment + human override
  + stated reason, all retained.
- Reversibility in record — because originals are never mutated, an erroneous
  override is itself just another overlay to correct.
- Legal/compliance-grade audit on a 7-year horizon, isolated from the
  security audit log.

### Negative
- Two audit tables to operate. Accepted: `verification_audit_log` and
  `auth_audit_log` have genuinely different schemas, retention, and query
  patterns; merging them couples intelligence audit to security audit.
- Read paths must compose "latest review wins" over the original — a small
  query cost for a large integrity gain.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Mutate the claim/object in place on override | Destroys the engine's judgment; "what did the system decide" becomes unanswerable. |
| One shared audit log with auth events | Couples security and intelligence audit; different retention and access policies collide. |
| Optional override note | Defeats accountability; an unexplained override is an unauditable one. |
| Hard-delete superseded claims | No conflict-resolution history; analysts can't review why a claim lost. |
