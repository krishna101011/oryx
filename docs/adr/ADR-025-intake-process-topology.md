# ADR-025 — Intake Process Topology

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-018 (outbox), ADR-014 (event architecture)

---

## 1. Context

Intake work is long-running and vendor-bound: a Gmail bootstrap can take
minutes; a sick RSS endpoint can hang to timeout. If sync work shares a
process with the HTTP API, an API deploy or restart pauses every
workspace's intake, and a slow vendor steals event-loop time from user
requests. Revision 1 left the topology implicit; CR-7 pins it.

## 2. Decision

Three processes per deploy unit, communicating only through Postgres:

```
process: api               uvicorn oryx.main:app
process: intake.scheduler  python -m oryx.services.intake.scheduler
process: queue.drainer     python -m oryx.services.queue.drainer
```

- **api** serves HTTP and never blocks on intake. Operational endpoints
  write intent (e.g. manual sync clears `last_attempt_at`); the scheduler
  acts on it.
- **intake.scheduler** picks due sources (interval, failure backoff,
  hourly degraded probe) and runs provider syncs behind per-kind
  concurrency semaphores, so one sick vendor cannot starve the others.
  It also hosts the hourly webhook-idempotency purge.
- **queue.drainer** drains `outbox_events` to the bus and hosts the
  hourly outbox/dead-letter cleanup. Its batch select uses
  `FOR UPDATE SKIP LOCKED`, so running a second drainer is safe — scale-out
  needs no code change.

Local development may colocate all three inside the API process with
`ORYX_DEV_MONOPROCESS=1`. The flag is honored **only when
`environment == "dev"`** — the environment check is the hard stop that
keeps a stray flag out of production. Worker imports stay local to the
lifespan hook so the production API process never loads worker wiring.

## 3. Consequences

### Positive
- API restarts don't pause sync; scheduler crashes don't drop HTTP traffic;
  drainer backpressure is isolated.
- Each process scales and is monitored independently (see the scheduler
  and drainer runbooks).

### Negative
- Three units to deploy and supervise instead of one — the price CR-7
  judged correct; the monoprocess flag keeps the dev loop simple.
- Cross-process coordination is via DB polling, not signals; worst-case
  latency between "user clicks sync" and execution is one scheduler tick.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Background tasks inside the API process | API restart pauses all intake; the failure CR-7 exists to prevent |
| Celery/RQ worker fleet | New broker + framework dependency for Phase 3 load (~67 syncs/min); §18.5 explicitly defers |
| One combined worker (scheduler+drainer) | Couples vendor-bound sync latency to event delivery latency; they degrade independently today |
