# Runbook — Dead-Letter Recovery

**Surface:** `/v1/admin/intake/dead-letter` (platform admin only)
**Owns:** triage, replay, and discard of poison outbox events
**Related:** drainer runbook, ADR-018

## When events land here

A row reaches `outbox_dead_letter` in exactly two ways:

1. **Attempts exhausted** — 20 delivery failures with exponential backoff.
   Usually a subscriber bug or a long downstream outage.
2. **`PermanentDeliveryError`** — a subscriber explicitly declared the
   payload unprocessable (schema violation, referenced row hard-deleted).

Dead-letter rows are retained 90 days, then deleted by the drainer's
cleanup job. Treat the queue as an ops inbox: it should normally be empty.

## Triage

```
GET /v1/admin/intake/dead-letter            # newest first, cursor-paginated
```

Each entry carries `eventName`, `finalError`, `totalAttempts`,
`workspaceId`, and `movedAt`. Triage by `finalError`:

- Same error across many events → subscriber bug. Fix the handler FIRST,
  then replay.
- Workspace-shaped errors ("workspace not found") on a deleted workspace →
  discard; the CR-6 cascade removed the data these events reference.
- One-off transient that outlived the retry budget (downstream was down
  for > the backoff horizon) → replay once the downstream is healthy.

## Replay

```
POST /v1/admin/intake/dead-letter/{id}/replay
```

Re-inserts the original envelope into `outbox_events` with fresh delivery
state (`attempts = 0`). The event **id inside the envelope is preserved**,
so subscriber-side idempotency keys still apply — replaying an event a
handler already processed is a no-op by contract. The dead-letter row is
removed; the response returns the new outbox row id for tracing.

Replay order is not guaranteed against live traffic. For Phase 3's single
event type (`intake.item.received`) ordering is immaterial; reconsider
before Phase 4 adds ordered flows.

## Discard

```
POST /v1/admin/intake/dead-letter/{id}/discard
```

Permanent. Use only when the event can never be valid again (workspace
deleted, payload predates a breaking fix that re-ingests from source).
Both replay and discard are structured-logged with the acting admin's
account id.

## Bulk situations

The API is intentionally one-at-a-time (each decision should be a
decision). For a mass subscriber-bug recovery after a fix, replay in
`movedAt` order oldest-first via a loop over the paginated list — and
watch the drainer's `drainer.pass` log line to confirm the replays drain
instead of bouncing back.
