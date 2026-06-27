# ADR-039 — Draft Version Control Model

**Status:** Accepted — implemented in Phase 5 Wave A (extended Waves B–C)
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-038 (generation model), ADR-042 (review policy), ADR-018 (outbox pattern)

---

## 1. Context

A draft is edited many times before it ships: the AI generates v1, the analyst
rewrites a paragraph, the AI regenerates with new instructions, the format is
switched, a reviewer sends it back and it is edited again. The naive model
overwrites a single `content` column on each change. That loses the one thing
this product most needs to be able to prove: **which words a human wrote and
which an AI generated**, and in what order. For verified financial intelligence,
the provenance of the prose is part of the audit trail.

## 2. Decision

**Append-only `draft_versions`, with a `current_version` pointer on the draft.
Nothing is ever overwritten.**

- Every state-changing operation — initial generation, regeneration, analyst
  save, format switch — INSERTs a new `draft_versions` row with the next
  `version_number` and flips `content_drafts.current_version` to it
  (`_append_version` in `services/drafts/service.py`). Version 1 is always the
  AI-generated draft.
- Each version row records `is_ai_generated` (True for generate/regenerate/
  format-switch, False for an analyst save), `edited_by`, optional `edit_note`,
  `word_count`, and `token_count`. That is the provenance ledger.
- The draft row carries the pointer and denormalised `word_count`; readers fetch
  "the current content" via `get_version(current_version)`, while history is the
  full ordered set of rows.
- Each append emits `content.draft.updated` on the outbox (ADR-018), so the
  event stream mirrors the version history.

This is **invariant #4** of the Wave A contract and is enforced uniformly: there
is exactly one private `_append_version` path, so no caller can accidentally
mutate content in place.

## 3. Consequences

### Positive
- Complete, ordered audit trail of human-vs-AI authorship — the provenance
  guarantee the product is built on.
- Trivial version history / diff UX: the rows already exist, ordered.
- Review (ADR-042) can pin a verdict to the exact `version_number` it judged.

### Negative
- `draft_versions` grows unbounded for heavily-iterated drafts. Accepted: rows
  are small (text + a few scalars) and a future retention policy can archive old
  versions without touching the current-pointer contract.
- "Current content" is a join/second-read, not a column on the draft. Accepted:
  the denormalised `word_count` covers the common list view, and the pointer read
  is a single indexed lookup.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single mutable `content` column | Destroys authorship provenance — the core reason the feature exists. |
| Versions but overwrite on analyst save | Re-introduces the same loss for exactly the edits a reviewer most needs to see. |
| Event-sourcing the content (replay deltas) | Far heavier; the outbox already gives an event stream, and full-snapshot rows are simpler to read and reason about. |
| Separate tables for AI vs human versions | Splits one ordered history into two; ordering across them becomes the hard problem a single table avoids. |
