# ADR-028: Conflict Resolution Policy

**Status:** Accepted
**Date:** 2026-06-15
**Phase:** 4

## Context

When two verified claims about the same subject assert mutually exclusive
things, the pipeline must decide whether a machine can safely pick a winner or
whether a human analyst must adjudicate. Auto-resolving too aggressively risks
silently discarding a true claim; escalating everything drowns analysts in
trivia. We need a conservative, auditable, reversible policy.

## Decision

Conflict detection runs on `verification.claim.verified` and has two paths:
a deterministic path that creates a conflict with no AI when an explicit
`contradicts` evidence link already ties the two claims' intake items, and an
AI path (`ConflictDetectorAI`, mutual-exclusion judgement) used only when the
subjects match, the predicates differ, and no contradiction link exists.

A detected conflict **auto-resolves only when ALL FIVE** conditions hold
(`services/conflicts/resolver.py`, pure + unit-tested individually):
1. `severity < 0.3`
2. one claim's confidence is `> 2×` the other's (latest complete run)
3. `conflict_type ∈ {factual_disagreement, temporal_inconsistency}`
4. neither claim already requires analyst review
5. neither claim's source has `accuracy_rate > 0.7`

`direct_contradiction` is therefore **never** auto-resolved (condition 3) — it
always escalates. Auto-resolution sets the loser's `superseded_by` to the
winner; escalation sets `requires_analyst_review = true` on both claims and
leaves the conflict `open`. Resolution is by **supersession via the
`superseded_by` FK — never a hard delete** — so the losing claim and its
history remain fully auditable and a later analyst can reverse the call.

## Consequences

- **Positive:** the default is conservative — anything genuinely ambiguous, or
  involving a high-trust source, or a direct contradiction, reaches a human.
  Every resolution (system or analyst) writes `verification_audit_log` and
  emits `verification.conflict.resolved`, so the decision and its five factor
  values are reconstructable.
- **Positive:** supersession is reversible and non-destructive; the conflict
  record is the durable artifact, recomposed objects follow via events.
- **Negative:** the five-condition gate is tuned by constants, not learned; it
  will need revisiting with production data. The AI path spends budget on
  same-subject/different-predicate pairs even when they turn out compatible.

## Alternatives Considered

- **Always escalate to an analyst.** Rejected: trivial low-severity
  disagreements between low-trust sources don't need human time, and the volume
  would make the queue useless.
- **Hard-delete the losing claim on resolution.** Rejected: destroys the audit
  chain and makes analyst reversal impossible; supersession keeps both.
- **A single learned classifier for "auto vs escalate."** Rejected for Phase 4:
  not explainable, not unit-testable per-condition, and we have no labelled
  data yet. The five explicit conditions are auditable today and can seed a
  model later.
