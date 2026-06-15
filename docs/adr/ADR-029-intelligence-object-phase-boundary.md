# ADR-029: Intelligence Object as the Analyze/Research Boundary

**Status:** Accepted
**Date:** 2026-06-15
**Phase:** 4

## Context

The verification pipeline produces per-claim facts: extracted claims, evidence
links, verification runs, conflicts. Analysts and the research surface need a
single assembled unit per source item — "what does this item, taken as a
whole, assert and how much do we trust it" — without re-deriving it from the
constituent rows every time. We also must guarantee that this assembled unit
never smuggles AI-written narrative into a system whose whole premise is
epistemic integrity.

## Decision

The **intelligence object** is the fan-in: one object per
`(workspace_id, intake_item_id)` (enforced by a UNIQUE constraint), composed
from the item's non-superseded claims. Composition
(`services/intelligence/composer.py`) fires from `CompositionTriggerHandler`
on `verification.claim.verified` and runs **only when ALL claims for the item
have reached a terminal state** (a `complete` or `failed` verification run) —
a partial item never composes.

Two hard content rules:
- **`headline` comes from `intake_items_normalized.subject`** (falling back to
  `sender_label`, then `"Untitled"`). It is **never AI-generated**.
- **`key_facts` is structured JSONB** keyed by claim subject
  (`{predicate, object, epistemicType, confidence}`). It is **never narrative
  prose**.

The object's `confidence_score` is the weighted-minimum aggregate of its
claims (ADR-027), capped at the weakest claim's epistemic ceiling, and its
`verification_status` reflects current conflict state (`contested` while any
constituent conflict is open). Composition is idempotent (an existing object
short-circuits) and does **not** auto-recompose on a `scoring_version` bump —
re-scoring is an explicit admin action (ADR-032).

## Consequences

- **Positive:** one queryable, scored unit per source item; the analyst and
  research surfaces read objects, not raw claim joins. Conflict lifecycle
  projects onto objects via events (`ObjectConflictProjector`), keeping conflict
  detection decoupled from the intelligence domain.
- **Positive:** the no-prose / structured-only rules make it impossible for the
  object to assert anything the underlying claims and intake data don't.
- **Negative:** the all-claims-terminal gate means a single stuck claim blocks
  the whole object; this is intentional but requires the admin re-run tools
  (ADR-032) to unstick. One-object-per-item also means an item that legitimately
  splits into unrelated topics is still a single object.

## Alternatives Considered

- **AI-generated headline/summary.** Rejected outright: it would let unverified
  narrative ride on top of a verification system; the headline must be
  traceable to intake data.
- **Compose eagerly on each claim verification.** Rejected: produces churn and
  half-formed objects; the terminal-state gate yields one stable composition.
- **No object; query claims directly each time.** Rejected: every consumer
  would re-implement aggregation and ceiling logic, and there'd be nowhere to
  attach an analyst verdict or a stable id for research packets.
