# ADR-032 — Verification Engine Versioning

**Status:** Accepted
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-027 (confidence composite), ADR-020 (normalizer versioning — precedent)

---

## 1. Context

Five distinct, independently-evolving pieces of logic shape a claim's
outcome: extraction, epistemic typing, evidence linking, verification logic,
and the scoring formula. Each will be revised at its own cadence — a prompt
tweak to the classifier should not invalidate the scoring of unrelated runs,
and a scoring-weight change should not force re-extraction of millions of
items.

Reproducibility is the governing requirement (ADR-027): a stored decision
must be re-derivable. That is impossible if logic versions are entangled or
if re-runs overwrite history. Phase 3's ADR-020 already established the
"version the derivation, keep the raw, rebuild offline" pattern for the
normalizer; Phase 4 generalizes it to the verification pipeline.

## 2. Decision

**Five independent version integers**, each a code constant, never stored as
configuration:

```
EXTRACTOR_VERSION   services/claims/extractor.py
CLASSIFIER_VERSION  services/claims/classifier.py
LINKER_VERSION      services/evidence/linker.py
ENGINE_VERSION      services/verification/engine.py
SCORING_VERSION     services/verification/scorer.py  (== CURRENT_SCORING_VERSION)
```

`CURRENT_SCORING_VERSION` lives in `core/scoring_version.py`. Version bumps
are **code deployments**, not DB writes — the database records which version
produced each row, never which version is "current."

**`verification_runs` is append-only.** A run is never deleted or
overwritten. Each row carries both `engine_version` and `scoring_version`.
Re-running produces a *new* row alongside the old; the latest run per claim
is the active one.

**Three admin re-run workflows**, all non-destructive:

- `reextract` — new claims at the current `extractor_version`, inserted
  alongside old; new claims flow the full pipeline.
- `reverify` — new `verification_runs` row per claim at current engine +
  scoring versions.
- `rescore` — recompute `confidence_score` on complete runs under a new
  `scoring_version`; update objects; emit `OBJECT_UPDATED`.

**Stale detection.** An intelligence object is stale when
`object.scoring_version < CURRENT_SCORING_VERSION`. The UI surfaces a "score
may be outdated" indicator with a recalculate CTA. Recalculation is a
**manual analyst action** — never automatic on version bump.

## 3. Consequences

### Positive
- Full reproducibility: any historical decision is re-derivable from its
  stored versions and inputs.
- Orthogonal evolution: a scoring change costs a `rescore`, not a
  re-extraction; a prompt change costs a `reextract` of only affected items.
- Complete audit trail — superseded runs persist for inspection.

### Negative
- Indefinite `verification_runs` retention grows storage. Accepted:
  reproducibility is worth the bytes; old partitions detach to cold storage.
  The retention/partition policy is governed separately and lands with
  Wave F as ADR-034 (forthcoming).
- Stale objects require manual recalc rather than auto-recompute. Accepted
  deliberately — auto-recalc on every version bump is a cost-and-noise
  hazard; the analyst decides when a re-score matters.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single global pipeline version | Couples unrelated changes; a classifier tweak would invalidate scoring reproducibility for free. |
| Overwrite-in-place verification runs | Destroys the audit trail; a re-run erases the prior decision that an analyst may have acted on. |
| Auto-recalculate all objects on `SCORING_VERSION` bump | Cost spike + notification noise across every workspace on every formula tweak; the stale indicator lets analysts opt in. |
| Store versions in DB config | Invites runtime drift between deployed code and recorded version; constants tie the version to the code that implements it. |
