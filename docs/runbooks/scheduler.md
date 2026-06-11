# Runbook — intake.scheduler

**Process:** `python -m anant.services.intake.scheduler`
**Owns:** source due-time selection, provider sync dispatch, webhook-idempotency purge
**Related:** ADR-025 (topology), drainer runbook, intake troubleshooting guide

## Normal operation

- Ticks every `SCHEDULER_TICK_SECONDS` (default 15s). Each tick selects
  enabled, pollable (`gmail`/`rss`/`api_pull`), `healthy`/`degraded`
  sources and dispatches the due ones behind per-kind semaphores
  (`SCHEDULER_PER_KIND_CONCURRENCY`, default 4).
- Log signals: `scheduler.started` on boot, `scheduler.tick {dispatched}`
  on non-empty ticks, `scheduler.idempotency_purged {deleted}` hourly.
- Due rules: healthy → per-source `fetch_interval_minutes` (defaults:
  gmail 15 / rss 30 / api_pull 15); failing → exponential backoff
  (30s·2ⁿ, 1h cap); degraded → hourly probe only; `auth_required` and
  `disabled` → never. `last_attempt_at IS NULL` means "due now" (new
  source or manual sync trigger).

## Start / stop / restart

```
# start (prod: one instance via the process supervisor)
python -m anant.services.intake.scheduler

# graceful stop: SIGTERM / Ctrl-C. In-flight syncs finish their item;
# cursors are only advanced after a completed sync, so a kill mid-sync
# re-pulls from the last committed cursor (idempotent by provider contract).
```

Restart safety: claiming a source stamps `last_attempt_at` *before* the
sync runs, so a crashed sync retries on the failure-backoff curve, not in
a hot loop.

## Symptoms → actions

| Symptom | Check | Action |
|---|---|---|
| No sources syncing anywhere | Is the process running? `scheduler.started` in logs? | Restart the process; check DB connectivity (`DATABASE_URL`) |
| One source never syncs | `intake_sources.status` | `auth_required` → user must reconnect (mobile → Source detail). `disabled` → re-enable via PATCH |
| Source stuck `degraded` | `last_error` on the row; `intake_audit_log` recent `sync_failed` entries | Fix the underlying vendor issue; next hourly probe recovers it, or clear `last_attempt_at` to force a probe now |
| `intake.sync_failed` flood, one kind | Vendor outage | Nothing — backoff + circuit breaker (§10.3) contain it; sources self-recover via probes |
| Manual sync button "does nothing" | Row's `last_attempt_at` should be NULL after the click | If set, the API write failed; if NULL and still nothing, scheduler is down (first row of this table) |
| Webhook idempotency table growing | `scheduler.idempotency_purged` absent from logs | Purge runs hourly inside this process — if it's down, keys accumulate (24h TTL each; bounded but check disk) |

## Scaling

One instance is the supported Phase 3 deployment. Per-kind semaphores
bound vendor concurrency inside it. If sync volume outgrows one process,
shard by workspace hash *before* reaching for a second unsynchronized
instance — two schedulers will double-claim sources (claims are
last-write-wins, harmless but wasteful).

## Vendor quotas

- Gmail: bootstrap is capped at 200 messages per sync; steady-state uses
  history deltas. 429s are honored via `Retry-After` (classifier).
- RSS: conditional requests (ETag/If-Modified-Since); default 30-min
  interval, floor 5 min.
- api_pull: per-endpoint page cap 20 pages per sync.
