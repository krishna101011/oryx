# ADR-047: Analytics Two-Source Model

**Status:** Accepted (Phase 7 Wave A, 2026-07-08)
**Context:** docs/PHASE_7_ARCHITECTURE.md §2 (frozen Rev 2.1) — this ADR propagates
the decision already made and frozen there into the ADR index; it does not make a
new one.

## Context

Phase 7 measures what Phases 2–6 already do. ADR-014 anticipated "Phase 7 reads
every event for analytics", and for genuine bus events that holds. But the Rev 1
verification pass (commit 1cf197d) found that three desired metric families are
produced by components that never publish to the bus: NotificationDispatcher
consumes events and writes `automation_log` decision rows without publishing
anything, and DigestWorker is a standalone tick scheduler (ADR-025 shape) that
records sends in `digest_runs`. A pure bus subscriber cannot observe those
outcomes.

## Decision

Two sources feed one read model:

- **Source A — bus subscriber.** `AnalyticsAggregator` registers in `build_bus()`
  exactly like NotificationDispatcher and writes one lightweight fact row per
  delivered catalog event to `analytics_events_raw` (workspace-scoped). The dedup
  key is the event envelope's own id — which is the outbox row's id
  (`services/queue/outbox.py` writes `OutboxEvent(id=uuid.UUID(event["id"]))`) —
  under a unique constraint, so at-least-once redelivery is a safe no-op.
- **Source B — direct aggregation.** Automation outcomes (dispatch/suppression
  decisions, push results, digest sends) are aggregated straight from
  `automation_log` and `digest_runs`, which are already idempotent via their own
  unique constraints. No second copy of that data is stored.

Both sources land in `analytics_rollups_daily` — one row per
(workspace_id, metric_key, date) — refreshed by a periodic tick worker
(DigestWorker's run_forever/tick/amain shape) that RECOMPUTES each day's value as
a fresh aggregate and upserts it. Nothing increments, so a repeated or concurrent
refresh always converges to the same values.

## Consequences

- Analytics is observational: the aggregator is one more bus handler and the
  rollup worker one more colocatable tick loop; neither is load-bearing for any
  other phase.
- Rollup values are workspace-scoped. `digest_runs` is account-scoped, so digest
  counts attribute to workspaces via `workspace_members`; an account in multiple
  workspaces would attribute its digests to each (a documented approximation that
  is exact while the product is single-workspace).
- Source A history begins at Wave A ship time — `analytics_events_raw` cannot be
  backfilled for events delivered before the subscriber existed. Source B
  metrics backfill their tables' full history on the first refresh.
- The two `workspace.deletion.*` cascade lifecycle events (published with
  `workspace_id=None`, outside the 20-event metric catalog) are not recorded —
  they carry no workspace to attribute a fact to and feed no metric.
