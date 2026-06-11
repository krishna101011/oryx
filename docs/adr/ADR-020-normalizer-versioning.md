# ADR-020 — Normalizer Versioning and Raw/Normalized Separation

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-019 (dedupe), ADR-006 (repository pattern)

---

## 1. Context

Normalization rules — URL canonicalization, HTML sanitization, sender
parsing — will change as Phase 4 learns what its verification engine
actually needs. If the raw provider payload and its normalized projection
share one row, every rule change forces either a destructive migration or
a vendor re-fetch. Vendor re-fetches are rate-limited (Gmail) or
impossible (a webhook that fired once).

## 2. Decision

Two tables with strictly different mutability:

- **`intake_items`** is the immutable system of record. `payload` holds
  the full provider raw, verbatim. After insert, only `deleted_at` ever
  changes.
- **`intake_items_normalized`** is a derived projection, rebuildable at
  any time from raw. Every row carries `normalizer_version`
  (`services/normalization/version.py`, `NORMALIZER_VERSION`).

Rules evolution is therefore: bump `NORMALIZER_VERSION`, deploy, run the
offline backfill (`INSERT ... SELECT` over rows with an older version).
No vendor traffic, no customer-facing outage, no migration on the raw
table.

The normalizer itself is a pure, stateless function
(`normalize_raw_item`) so a backfill produces byte-identical output for
identical input.

## 3. Consequences

### Positive
- Phase 4 can demand new normalized fields without touching transport.
- "What arrived" vs "what we derived" stays a hard line (§1.3 of the
  architecture) — verification policy operates on a clean record.
- Backfills are observable: rows still on version N are countable.

### Negative
- Storage duplication for body text (accepted in §11.7; ~2 GB/year per
  heavy workspace, revisit past 1M items per workspace).
- A second write per ingest.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| One table, normalize in place | Rule changes destroy provenance; re-fetch often impossible |
| Normalize lazily at read time | Pushes vendor-specific parsing into every consumer; Phase 4+ would re-implement |
| Store only normalized | Loses the immutable raw record that makes Phase 4's trust line meaningful |
