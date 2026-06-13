# ADR-036 — Epistemic Type System

**Status:** Accepted — implemented in Phase 4 Wave A (`76c3c9e`)
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-027 (confidence composite), ADR-037 (claims-evidence separation)

> **Numbering note.** The Rev 3 Phase 4 blueprint proposed this as ADR-024.
> That number is already taken by a frozen Phase 3 ADR
> (`ADR-024-unified-intake-sources-table`). To avoid overwriting frozen
> history, this decision is recorded at **ADR-036** while the blueprint's
> ADR-026–035 keep their numbers; the companion relocation is ADR-037
> (claims-evidence separation, from the blueprint's ADR-025).

---

## 1. Context

A confidence score without an epistemic anchor is a lie waiting to happen. If
a *rumor* that accumulates fifty corroborating sources can climb to 0.90,
the score has silently equated "widely repeated" with "true" — the exact
epistemic failure the intelligence layer exists to prevent. The system needs
a typed classification of *what kind of assertion* a claim is, established
before any score is computed, with a permanent bound on how confident the
system may ever be about that kind.

## 2. Decision

Every claim carries an **epistemic type**, one of six:
`fact · claim · rumor · speculation · opinion · unclassified`.

**Typed before scored.** Classification (Wave A `EpistemicClassifierAI`)
runs before verification. An `unclassified` claim is **unverifiable by
definition** and produces a `null` confidence score — it cannot influence
anything until typed.

**The hierarchy flows downward only.**
- An analyst may **demote** a claim's type (override, ADR-033).
- The system **never auto-promotes**. No volume of evidence moves an
  `opinion` toward `fact`. Volume is not epistemic status.

**Conservative ambiguity defaults** (enforced in code, not just the prompt):
```
ambiguous fact vs claim    → claim
ambiguous claim vs rumor    → rumor
ambiguous rumor vs opinion  → rumor
```
When the classifier is unsure, it errs toward the *lower-trust* type. Over-
verification is recoverable via analyst override; epistemic inflation is not.

**Permanent ceilings by type** (applied after the score composite, ADR-027):
```
fact 1.00 · claim 0.85 · speculation 0.60 · rumor 0.40 · opinion 0.30
unclassified → null (no score)
```
The ceiling is a property of the type, not of the evidence. A rumor's ceiling
is 0.40 no matter how it is corroborated.

## 3. Consequences

### Positive
- The confidence score keeps its meaning: a 0.40 rumor and a 0.40 contested
  fact are honestly different objects, and neither masquerades as the other.
- Epistemic inflation is structurally impossible — the ceiling caps it and
  auto-promotion is forbidden.
- Conservative defaults bias the whole system toward under-claiming, which is
  the recoverable error.

### Negative
- A misclassification at extraction propagates downstream (a true fact typed
  as a claim is capped at 0.85). Mitigated by: the analyst review queue,
  conservative defaults erring low (rarely the dangerous direction), and
  versioned re-classification (ADR-032) that re-runs without data loss.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single score range, no epistemic type | A heavily-repeated rumor reaches fact-like scores — semantically false; the score stops meaning anything. |
| Permissive ambiguity defaults (fact-leaning) | Epistemic inflation that is hard to walk back; analysts inherit inflated trust. |
| Auto-promotion by corroboration volume | Conflates "widely repeated" with "true" — the precise failure the layer exists to prevent. |
| Ceiling as a function of evidence, not type | Lets volume override type; reintroduces the inflation the ceilings are there to stop. |
