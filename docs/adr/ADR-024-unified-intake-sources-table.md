# ADR-024 — Unified `intake_sources` Operational Table

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-010 (workspace from day one), ADR-025 (process topology)

---

## 1. Context

Phase 2 shipped two user-facing selection tables: `workspace_sources`
(catalog picks) and `workspace_custom_sources` (user-added URLs). Phase 3
Revision 1 proposed an `intake_source_state` table whose `source_id`
pointed at **either** of them — a polymorphic foreign key. Staff review
(CR-1) flagged this as the single largest structural footgun in the
design: no DB-level constraint can enforce a polymorphic FK, every join
needs a discriminator branch, and cascade deletes have undefined meaning.

## 2. Decision

One unified operational table, `intake_sources`, owned by the
orchestrator — one row per operational source regardless of kind:

- Identity + behavior: `kind` ('gmail'|'rss'|'webhook'|'api_pull'|'manual'),
  `enabled`, per-provider `config` (jsonb).
- Runtime state, absorbed from the abandoned state table: opaque
  provider-shaped `cursor` (jsonb), `last_synced_at`, `last_attempt_at`,
  `consecutive_failures`, `status`, `last_error`.
- Origin link back to the Phase 2 selection rows as **soft pointers**
  (`origin_kind` + `origin_catalog_key` | `origin_custom_id`), explicitly
  not FK-enforced: the user-facing selection row and the operational row
  have independent lifecycles (a selection can be disabled and restored
  while history stays attributable; disabling a selection soft-disables —
  never deletes — the operational row).

Every Phase 3 table that needs a source FK (`intake_items`,
`intake_credentials`, `intake_audit_log`, `webhook_idempotency_keys`)
points at `intake_sources.id` — a real, constraint-enforced FK.

The `cursor` stays jsonb because every provider's resume token is shaped
differently (Gmail `historyId`, RSS `(etag, last_modified)`, api_pull
per-endpoint tokens); the orchestrator never inspects it.

## 3. Consequences

### Positive
- The scheduler, runner, routers, and CR-6 cascade all talk to exactly one
  table; joins are unambiguous; deletes cascade correctly.
- Adding a provider kind is an enum value + provider folder — no schema
  surgery.

### Negative
- Selection state and operational state can drift if the sync glue between
  Phase 2 rows and `intake_sources` rows has bugs — accepted, because the
  drift is observable and repairable, unlike a broken polymorphic join.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Polymorphic FK (Revision 1) | No DB constraint, ambiguous joins, undefined cascades — CR-1 |
| Two parallel state tables (one per Phase 2 table) | Doubles every orchestrator query and every future provider's wiring |
| Fold operational state into the Phase 2 tables | Couples user-facing selection lifecycle to orchestrator writes; breaks the §13.3 two-lifecycle split |
