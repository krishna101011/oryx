# ADR-019 — Two-Tier Dedupe Fingerprint

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-020 (normalizer versioning)

---

## 1. Context

The same fact reaches intake through multiple doors: an article surfaced
via RSS and forwarded to Gmail, a webhook fired twice on vendor retry, one
message caught in two watched labels. Phase 3 dedupes per workspace with
two keys: a provider key `(workspace_id, intake_source_id, external_id)`
for re-ingestion within one source, and a cross-source content fingerprint.

Revision 1 drew the fingerprint as
`sha256(sender_domain, canonical_url, normalized_title)` with the URL
omitted when absent. Staff review (CR-2) caught the failure mode: a
body-only daily brief from the same sender with the same subject would
collapse across days — a recurring newsletter would be ingested once,
ever.

## 2. Decision

The fingerprint is two-tier, selected by item shape:

| Item shape | Fingerprint |
|---|---|
| Has an external link | `sha256(sender_domain, canonical_url(primary_link), normalize_title(subject))` |
| Body-only (no link) | `sha256(sender_domain, normalize_title(subject), date_bucket(received_at))` |

- `canonical_url` strips tracking params (utm_*, etc.), normalizes case,
  drops trailing slashes — so the "same" article shared two ways matches.
- `date_bucket` is `YYYY-MM-DD` in the workspace's timezone: same-title
  body-only items from *different days* are a recurring brief, not
  duplicates; same-day repeats still collapse.
- Dedupe scope is the workspace, never global: one tenant's "duplicate"
  is another's first sighting, and a global index would leak activity
  timing across tenants.
- First sighting wins. Later matches increment `duplicate_count` on
  `intake_dedupe_index` and are recorded in `intake_items_duplicates` for
  audit; no second raw row is written.

## 3. Consequences

### Positive
- Linked items dedupe across sources; body-only recurring content is not
  falsely collapsed.
- The decision is a pure function (`dedupe/fingerprint.py`) — unit-tested
  in isolation, including the timezone-sensitive date bucket.

### Negative
- Two formulas to reason about instead of one; the tier is recorded on
  ingest results so misclassification is observable.
- A body-only item later re-sent *with* a link is a different fingerprint
  (accepted: the linked version carries more information).

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single formula, URL optional | CR-2 false positive: collapses recurring body-only briefs across days |
| Fuzzy/similarity hashing (simhash) | Verification-adjacent judgement; Phase 4's job, not transport's |
| Global cross-tenant dedupe | Tenant isolation violation; leaks timing across workspaces |
