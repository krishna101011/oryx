# ADR-026 — Evidence Search Strategy

**Status:** Accepted (LOCKED) — implemented in Phase 4 Wave B (`7b55fcc`)
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-037 (claims-evidence separation), ADR-027 (confidence composite)

---

## 1. Context

Phase 4's evidence stage must, for every typed claim, find the intake-corpus
items that bear on it (corroborate, contradict, contextualize). The corpus
is `intake_items_normalized` — Phase 3's append-only, workspace-scoped
projection of every ingested item.

Two retrieval families were on the table:

- **Lexical** — Postgres full-text search (BM25-equivalent `ts_rank` over a
  `tsvector` GIN index). Term-overlap ranking, no model, no new infra.
- **Semantic** — `pgvector` (or an external vector DB) over embeddings.
  Captures paraphrase and conceptual similarity, but requires an embedding
  pipeline, a vector index, and per-item embedding cost at intake time.

At Phase 4 launch the corpus is shallow: early workspaces have tens to low
hundreds of items. Semantic recall's advantage (finding non-lexically-similar
matches) only pays off at corpus depth the product does not yet have, while
its infrastructure cost is paid from day one.

## 2. Decision

Evidence search is **lexical BM25 via Postgres full-text search**, against
the GIN expression index created in Wave A (`idx_intake_normalized_fts`):

```
to_tsvector('english', coalesce(subject,'') || ' ' || coalesce(body_text,''))
```

`BM25Searcher` runs a two-stage query, ranked by `ts_rank` descending,
`LIMIT 20`:

1. **Primary** — `plainto_tsquery` of `subject + ' ' + predicate`.
2. **Fallback** — `subject` only, run only if the primary returns zero rows.
3. Zero rows after both is a valid result: the corpus may be sparse, and a
   claim with no corroboration proceeds to verification with no evidence.

The query joins `intake_items` for the `workspace_id` scope, `received_at`,
and `source_id` (the normalized projection carries no workspace column), and
excludes the claim's own intake item. Only a 500-char `body_text` excerpt
crosses into the AI linker — a cost guard, not a ranking input.

`pgvector` semantic search is a **documented upgrade path**, not a Phase 4
item. The `BM25Searcher` interface is the seam: swapping the implementation
behind it requires no change to `EvidenceService`, the linker, or the
schema.

## 3. Consequences

### Positive
- Zero new infrastructure: the index is one additive GIN index on a Phase 3
  table; the query is plain SQL the planner already understands (verifiable
  via `EXPLAIN ANALYZE`).
- Transparent and debuggable — a human can read the query and predict the
  hits. No opaque embedding space to reason about.
- Reuses the database the system already runs. No embedding cost at intake.

### Negative
- Lexical only: a paraphrased corroboration with no shared terms is missed.
  Accepted because (a) the corpus is too shallow for semantic recall to add
  meaningful coverage at launch, and (b) the subject-only fallback widens
  recall for the common "same entity, different wording" case.
- English-stemmed `tsvector` — non-English corpora degrade. Revisit with the
  i18n phase, alongside the semantic upgrade.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| `pgvector` semantic search now | Embedding pipeline + vector index cost paid from day one for recall the shallow launch corpus can't exercise; classic premature optimization. Kept as the explicit upgrade path behind the `BM25Searcher` seam. |
| External vector DB (Pinecone/Weaviate) | A whole new operational dependency and failure mode for a retrieval problem Postgres FTS solves at current scale. |
| Elasticsearch | Second datastore to run, sync, and secure; duplicates the corpus; no Phase 4 justification. |
| No fallback (subject+predicate only) | Predicate terms over-narrow the query; the subject-only fallback materially improves recall on sparse corpora at negligible cost. |
