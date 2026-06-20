# Runbook — queue.drainer

**Process:** `python -m oryx.services.queue.drainer`
**Owns:** outbox delivery, dead-letter promotion, outbox/dead-letter cleanup
**Related:** ADR-018 (outbox), dead-letter recovery runbook

## Normal operation

- Loops: select up to `DRAINER_BATCH_SIZE` (default 100) undelivered
  `outbox_events` in creation order (`FOR UPDATE SKIP LOCKED`), publish
  each due row to the bus, stamp `delivered_at`. Sleeps 1s after a busy
  pass, 5s when idle.
- Delivery is **at-least-once**: publish happens before the commit, so a
  crash in between redelivers. All subscribers must stay idempotent
  (ADR-014 §2.5).
- Retries back off per row: 5s·2ⁿ capped at 15 min. After 20 attempts —
  or a `PermanentDeliveryError` from a handler — the row moves to
  `outbox_dead_letter`.
- Hourly cleanup: delivered rows older than 7 days and dead-letter rows
  older than 90 days are deleted. Log signals: `drainer.started`,
  `drainer.pass {delivered,retried,dead_lettered}` (only on non-clean
  passes), `drainer.cleanup {counts}`, `drainer.dead_lettered`.

## Health queries

```sql
-- Backlog (should hover near zero)
SELECT count(*) FROM outbox_events WHERE delivered_at IS NULL;

-- Oldest undelivered (delivery lag)
SELECT now() - min(created_at) FROM outbox_events WHERE delivered_at IS NULL;

-- Retry-looping events
SELECT id, event_name, attempts, last_error FROM outbox_events
WHERE delivered_at IS NULL AND attempts > 3 ORDER BY attempts DESC LIMIT 20;
```

## Symptoms → actions

| Symptom | Check | Action |
|---|---|---|
| Backlog growing | Is the process up (`drainer.started`)? | Restart; verify DB connectivity |
| Backlog growing, process up | `drainer.pass` shows high `retried` | A subscriber is failing — read `last_error` on the rows; fix the handler; rows self-retry |
| Same event ids cycling | `attempts` climbing on specific rows | Let them hit the 20-attempt cap → dead-letter, then use the dead-letter recovery runbook |
| `delivered` always 0, no errors | No subscribers registered (Phase 3 ships none — empty fan-out marks delivered). If 0 *and* backlog grows, the publish path itself is failing | Inspect exceptions in logs |
| Outbox table large | Cleanup running? `drainer.cleanup` hourly in logs | If the process was down for days, the first cleanup pass handles it; no manual action |

## Restart / crash semantics

Safe at any moment. Undelivered rows are re-selected next pass; a row
published-but-uncommitted at crash time is redelivered (idempotent
handlers absorb it). `SKIP LOCKED` makes an accidental second instance
harmless — rows are never double-published concurrently.

## Scaling

Single process sustains Phase 3 load (§18.1) with headroom to ~500
events/s. Past that, the ADR-014 Stage C broker swap is the move — not
more drainers.
