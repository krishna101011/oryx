# ADR-027 — Confidence Score Composite

**Status:** Accepted
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-036 (epistemic type system), ADR-031 (source credibility), ADR-032 (engine versioning)

---

## 1. Context

Verification must attach a single, bounded `0.0–1.0` confidence number to
each claim. The number drives analyst triage, the UI confidence tiers, and
the weighted-minimum aggregation into intelligence objects. It must be:

- **Deterministic and reproducible** — same inputs + same `scoring_version`
  produce the same score, byte for byte. An analyst's decision rests on it.
- **Auditable** — every contributing factor stored, not just the result.
- **AI-free** — a model-judged score is neither reproducible nor explainable,
  and couples the trust layer to a model version.

The score must also never contradict the claim's epistemic ceiling (ADR-036):
a rumor cannot score like a fact regardless of corroboration volume.

## 2. Decision

Confidence is a **weighted sum of six factors, then an epistemic ceiling**,
computed in pure arithmetic (`ConfidenceScorer`, no AI):

| Factor | Weight | Source |
|---|---|---|
| `source_trust_score` | 0.25 | `source_credibility_records.accuracy_rate` |
| `cross_reference_count_score` | 0.25 | normalized 0→0.0, 1→0.4, 2→0.7, 3+→1.0 |
| `evidence_strength_score` | 0.20 | weighted mean of `link.strength` |
| `recency_score` | 0.10 | `exp(-age_hours / 168)` |
| `claim_specificity_score` | 0.10 | object null→0.2, ≤3 tokens→0.5, >3→1.0 |
| `primary_source_available` | 0.10 | 1.0 if a `primary_source` evidence link exists |

Weights sum to exactly **1.00** (test-asserted).

**Zero cross-reference renormalization.** When `cross_reference_count = 0`,
that factor is *excluded from the denominator* and the remaining five weights
are renormalized to sum to 1.00. Absence of corroboration does **not**
collapse the composite to zero — a single well-sourced item is scored on its
own merits.

**Epistemic ceiling applied after the composite** (ADR-036): `min(composite,
ceiling[epistemic_type])`. `unclassified` returns `null` — no score.

**Evidence strength weights** (by `evidence.evidence_type`) feed the strength
mean: primary_source 1.0, corroboration 0.7, secondary_source 0.5, context
0.3, inference 0.2, contradiction 0.0 (excluded from the mean).

**Read provenance** (deliberate and tested): the scorer reads `link.strength`
and `link.relationship` from `claim_evidence_links` for the logic and the
strength factor. The **one exception** is `primary_source_available`, which
reads `evidence.evidence_type`. This asymmetry is intentional — the link
carries the per-claim judgment; the evidence row carries the intrinsic
source character.

Weights, normalization, ceilings, and strength weights are all governed by
`scoring_version` (ADR-032); changing any is a version bump, never a silent
edit.

## 3. Consequences

### Positive
- Fully reproducible and explainable: every factor is stored in
  `verification_runs.factors`; the UI renders the breakdown.
- No model dependency — a scoring change is a code deploy + `rescore`, not a
  re-extraction or a prompt iteration.
- Ceilings keep the score semantically honest across epistemic types.

### Negative
- The weights are expert judgment, not learned. Accepted: they are
  transparent, versioned, and revisable; an opaque learned weighting would
  fail the reproducibility and explainability bars.
- Recency decay (168h half-life) is a fixed prior; revisit per-topic decay
  if analytics show it mis-serves slow-moving subjects.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| ML-learned scorer | Opaque, non-reproducible across model versions, unexplainable to analysts — fails the core bars. |
| Simple average of factors | Hides a catastrophically weak factor; no principled handling of the zero-cross-reference case. |
| AI-judged confidence | Couples the trust layer to a model; same input yields different scores across runs; unauditable. |
| Collapse to zero on zero cross-references | Punishes genuinely novel single-source facts as if unsourced; renormalization scores them on their remaining merits instead. |
