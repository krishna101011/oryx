# ADR-031 — Source Credibility Evolution

**Status:** Accepted
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-027 (confidence composite), ADR-032 (engine versioning)

---

## 1. Context

`source_trust_score` is the single largest weight in the confidence composite
(0.25, ADR-027). It must come from somewhere on day one — before any
verification has run — and it must improve as the system observes whether a
source's claims hold up.

Phase 2 already records a curated `source_catalog.editorial_confidence`
(INTEGER, 0–100). Phase 4 needs a *running, per-workspace, evolving* accuracy
record that starts from that editorial prior and updates from verification
outcomes. Two failure modes must be designed out: a cold-start blind spot
(no record → no score) and a units mismatch (0–100 integer vs 0.0–1.0 float)
that would corrupt every score with no runtime error.

## 2. Decision

`source_credibility_records`, keyed **`(workspace_id, source_id)`** — credibility
is per-workspace; one workspace's trust in a source is independent of
another's.

**Bootstrap (migration 0006, mandatory conversion):**

```sql
accuracy_rate = COALESCE(editorial_confidence, 50) / 100.0
```

The `/ 100.0` is **not optional** — `editorial_confidence` is INTEGER 0–100,
`accuracy_rate` is FLOAT 0.0–1.0. Omitting the division yields `accuracy_rate
= 75.0` instead of `0.75` and silently corrupts every `source_trust_score`
from day one with no error. A migration unit test asserts `75 → 0.75` and
`NULL → 0.5` (neutral prior). This is logged as risk R9 (CRITICAL) precisely
because it fails silently.

**Evolution.** After each verification run, `CredibilityUpdater` adjusts the
source's record in the *same transaction* as the run: `verified_claim_count`,
`contested_claim_count`, `total_claim_count`, and a recomputed `accuracy_rate`.
The feedback loop needs no manual curation.

**Reserved, unused in Phase 4.** `topic_reliability` (JSONB) and
`bias_indicators` (JSONB) columns exist but are not read by Phase 4 scoring.
They are forward-compatibility seams — adding a column later is a migration;
keeping an unused column is free.

## 3. Consequences

### Positive
- Editorial autonomy: Reuters in Workspace A and Workspace B evolve
  independently from each workspace's own verification history.
- Cold-start handled: the editorial prior seeds the score; `NULL` editorial
  confidence falls back to a neutral 0.5.
- Self-improving without human curation; every update is transaction-atomic
  with the run that caused it (no drift between a run and its credibility
  effect).

### Negative
- Thin signal early — until runs accumulate, `accuracy_rate` is mostly the
  bootstrap prior. Accepted: the prior is a reasonable starting estimate and
  the loop converges with volume.
- Per-workspace records multiply row count by workspace. Accepted: the PK is
  `(workspace_id, source_id)` and the table is small relative to runs.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Global source credibility | Breaks workspace editorial autonomy; one workspace's contested source would taint another's trusted one. |
| No bootstrap (start at 0.5 always) | Discards the curated editorial signal the product already has; every source starts blind. |
| Manual analyst curation of accuracy | Does not scale; the point is an automatic feedback loop. |
| Store `accuracy_rate` as 0–100 to match editorial | Forces the scorer to divide on every read and invites the same units bug at a worse layer; convert once, at the boundary. |
