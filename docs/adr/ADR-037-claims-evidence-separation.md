# ADR-037 — Claims–Evidence Separation

**Status:** Accepted — implemented in Phase 4 Waves A–B
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-036 (epistemic type system), ADR-027 (confidence composite), ADR-026 (evidence search)

> **Numbering note.** The Rev 3 Phase 4 blueprint proposed this as ADR-025.
> That number is already taken by a frozen Phase 3 ADR
> (`ADR-025-intake-process-topology`). To avoid overwriting frozen history,
> this decision is recorded at **ADR-037**, paired with ADR-036 (epistemic
> type system, from the blueprint's ADR-024).

---

## 1. Context

A claim (an atomic subject/predicate/object assertion extracted from one
intake item) and evidence (a corpus item that bears on a claim) are different
things with different lifecycles. The tempting shortcut is a single
`verification_items` table that conflates them. The question is whether the
verification model should treat "the thing being judged" and "the thing
judging it" as one entity or two.

The relationship is also genuinely many-to-many: one corpus item can
corroborate claim A while contradicting claim B, and one claim draws on many
corpus items. A shared table cannot express that without becoming a join
table in disguise.

## 2. Decision

Three tables.

- **`claims`** — the assertions under verification (Wave A). Extraction- and
  typing-versioned; epistemically typed (ADR-036).
- **`evidence`** — corpus passages relevant to claims (Wave B). **Immutable
  once written.**
- **`claim_evidence_links`** — the N:M join carrying the *judgment*:
  `relationship` (supports / contradicts / contextualizes), `strength`
  (0.0–1.0), `linker_version`. PK `(claim_id, evidence_id)`.

**The link, not the evidence row, drives verification logic.** The engine
reads `link.relationship`; the scorer reads `link.strength`. The single,
deliberate exception is `primary_source_available`, which reads
`evidence.evidence_type` (ADR-027) — the link carries the per-claim judgment;
the evidence row carries the intrinsic source character.

**Evidence immutability + `source_deleted`.** Evidence is never edited; if its
originating intake item is soft-deleted, the `source_deleted` flag is set
rather than the row removed. Historical `verification_runs` reference evidence
by id and must remain reproducible (ADR-032) — deleting evidence would corrupt
the audit chain.

**One evidence row per `(workspace_id, intake_item_id)`**, reused across the
claims it bears on; the differing per-claim verdicts live on the links.

## 3. Consequences

### Positive
- Claims and evidence evolve their schemas independently; extraction is
  decoupled from sourcing.
- The N:M link expresses the real semantics — one corpus item supporting one
  claim and contradicting another, each with its own strength.
- Immutable evidence + versioned links keep historical runs reproducible.

### Negative
- More tables and joins than a single `verification_items` table. Accepted:
  the join is the model, not overhead — collapsing it would re-encode the
  same relationship as nullable columns and lose the per-claim verdict.
- A dedup lookup (`find_evidence_for_item`) guards the one-row-per-item rule
  rather than a DB unique constraint (safe under the single-drainer
  topology); promote to a constraint if a second writer is ever added.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single `verification_items` table | Conflates the judged and the judging; cannot express one item supporting claim A and contradicting claim B without a join table anyway. |
| Evidence embedded in the claim row | No reuse of a corpus item across claims; duplicates text and re-runs the linker needlessly. |
| Cascade-delete evidence when its source is deleted | Corrupts historical verification runs that reference it; `source_deleted` preserves the audit trail while marking the gap. |
| Drive verification from `evidence.evidence_type` instead of the link | Loses the per-claim relationship; the same evidence type can support one claim and contradict another. |
