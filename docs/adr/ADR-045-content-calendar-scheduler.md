# ADR-045 — Content Calendar Scheduler

**Status:** Accepted — implemented in Phase 5 Wave E
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-025 (intake process topology), ADR-044 (publishing idempotency), ADR-040 (channel adapter protocol)

---

## 1. Context

Drafts can be scheduled to publish at a future time rather than immediately.
Something must wake up, notice that a scheduled entry is due, and fire it through
the publishing engine — and must do so reliably across process restarts and
downtime, without double-firing and without silently publishing something wildly
late. Phase 3 already established how recurring background work is run in this
codebase (the intake scheduler and the outbox drainer); the calendar must follow
that pattern, not invent a new one.

## 2. Decision

**A standalone worker process — `python -m oryx.services.calendar.scheduler` —
matching the intake scheduler / drainer shape exactly: a tick loop +
`run_forever` + `amain`. It is NOT an in-request background task.**

Verified against `services/calendar/scheduler.py`:

- **60-second tick** (`DEFAULT_TICK_SECONDS = 60.0`), with the **first tick run
  immediately at startup** (before the first sleep) so a downtime backlog is
  caught right away rather than waiting a full interval.
- **Two passes per tick.**
  - *Pass A — calendar firing.* Due `scheduled` entries within the **15-minute
    grace window** (`GRACE_WINDOW`) fire through the existing
    `PublishingEngine.publish_draft`; the per-target result maps onto the entry
    (delivered → published, failed → failed, pending → left scheduled for Pass B).
    An entry reached **beyond** the grace window is marked `failed` **without
    publishing** — a visible miss beats a wildly-late silent publish (§19.3).
  - *Pass B — transient retry re-drive.* Publications left `pending` by a
    transient failure are re-driven with **exponential backoff** keyed on
    `attempt_count` (`RETRY_BACKOFF`: 5 min → 30 min → 2 hr, with a row at
    attempt 4 reusing 2 hr so it is never stranded). Re-drive calls the *same*
    `publish_draft`, which handles the pending row idempotently (ADR-044) and
    advances `attempt_count`/`last_attempt_at`/`status` itself — no second retry
    loop is built here.
- **One bad entry never kills the loop** — `fire_due_entries` and
  `redrive_pending` catch per-item, log with the entry/publication id, and
  continue.

**Local-dev colocation via `ORYX_DEV_MONOPROCESS`.** In `environment=dev` only,
setting `oryx_dev_monoprocess=1` colocates all three workers (intake scheduler,
queue drainer, calendar scheduler) into the API process lifespan
(`should_colocate` in `main.py`); production always runs three separate processes.

**The silent-failure incident this ADR exists to record.** `Settings` has no
`env_prefix`, field names map directly to env-var names, and the config uses
`extra="ignore"`. After the `anant→oryx` rename, a stale `ANANT_DEV_MONOPROCESS=1`
line in a developer's gitignored `.env` bound to **nothing** — silently ignored,
field fell back to its default — so the API started with monoprocess **off and no
workers**, with zero diagnostic. Because the per-worker `*.started` log lines live
only in each worker's standalone `amain()`, colocated mode (which calls
`run_forever()` directly) produced no startup evidence either way. Wave F's fix:
the lifespan now emits an explicit `monoprocess.workers_started` (with the worker
names and count) when colocation engages, and `monoprocess.disabled` when it does
not — so a misconfigured flag is now loud, not silent. This is called out
explicitly here, not left implicit, precisely because the failure mode was
invisible.

## 3. Consequences

### Positive
- Identical operational shape to the existing workers — same deploy, same
  monitoring, same mental model; no novel background-task mechanism.
- Startup catch-up + grace window + backoff make it robust to restarts and
  downtime without double-firing (idempotency is delegated to the engine).
- The grace window encodes an explicit editorial choice: a late-enough publish is
  worse than a recorded miss.
- Colocation now self-reports, closing the silent-misconfiguration gap.

### Negative
- A 60-second tick means up-to-~60s firing latency vs the scheduled time.
  Accepted: content scheduling is not sub-minute-sensitive, and the grace window
  is 15 minutes wide.
- Two passes per tick scan two query sets each minute. Accepted: both are indexed
  and bounded; the cost is trivial against the tick interval.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| In-request / in-API-process background task (`asyncio.create_task` per request) | Dies with the request, doesn't survive restart, can't be deployed/scaled independently; contradicts the established worker topology (ADR-025). |
| A cron/external scheduler | Adds an external dependency and a second deploy surface; the in-codebase tick-loop pattern already exists and is proven. |
| Publish wildly-late entries anyway | A surprise publish hours after the intended time can be actively harmful for time-sensitive financial content; a visible miss is safer (§19.3). |
| Build a second retry loop in the scheduler | Duplicates the engine's idempotent pending-row handling; re-driving the same `publish_draft` reuses one correct path. |
| Leave colocation un-logged | The silent ANANT_-prefix incident proved an un-logged worker start is undebuggable; the explicit log line is the cheap, durable fix. |
