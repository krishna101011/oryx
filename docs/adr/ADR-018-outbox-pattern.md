# ADR-018 — Outbox Pattern from Phase 3 Day 1

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-014 (event architecture), ADR-025 (process topology)

---

## 1. Context

ADR-014 staged the event infrastructure: Stage A (in-process bus) through
the end of Phase 3, Stage B (persistent outbox) at Phase 4. The Phase 3
architecture review (Rev 2, CR-3) reversed that for intake: Phase 4's
verification engine cannot afford lost `intake.item.received` events on a
process restart, and intake is the system's single entry door — losing
its events silently breaks every downstream phase.

## 2. Decision

Phase 3 skips Stage A and ships Stage B directly:

- Every ingest transaction writes the `DomainEvent` envelope to
  `outbox_events` **in the same transaction** as the `intake_items` /
  `intake_items_normalized` / `intake_dedupe_index` rows (the four-write
  transaction). A crash between state change and publish is impossible by
  construction.
- A separate `queue.drainer` process (ADR-025) selects undelivered rows in
  creation order with `FOR UPDATE SKIP LOCKED`, publishes to the
  `EventBus`, and stamps `delivered_at`. Delivery is at-least-once;
  handlers stay idempotent per ADR-014 §2.5.
- Retries back off exponentially per row (5s base, 15-minute cap). Rows
  exceeding 20 attempts — or raising `PermanentDeliveryError` — are
  promoted to `outbox_dead_letter` (CR-3) with the final error preserved.
- Retention is bounded: delivered rows are pruned after 7 days by the
  drainer's hourly cleanup; dead-letter rows after 90 days. A platform-admin
  surface (`/admin/intake/dead-letter`) lists, replays, and discards
  dead-letter entries; replay re-inserts the original envelope with fresh
  delivery state so handler-side idempotency keys still apply.

## 3. Consequences

### Positive
- Phase 4 subscribes to a replayable, crash-safe stream from its first day.
- Poison events are isolated and operable instead of wedging the queue.
- The `EventBus` seam is untouched — swapping to a broker (Stage C)
  remains a one-line wiring change.

### Negative
- One more process to deploy and monitor (accepted; see ADR-025).
- Outbox table churn adds write amplification per ingest (~1 row); bounded
  by the 7-day cleanup.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Stage A in-process bus as originally staged | Restart loses undelivered events; intake replay-from-vendor is rate-limited and slow |
| Broker (Redis Streams/NATS) now | Infrastructure burden with one consumer; ADR-014 already reserves this as Stage C |
| Unbounded outbox, no dead-letter | Two "grows forever" footguns; poison events retry indefinitely |
