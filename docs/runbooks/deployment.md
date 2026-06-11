# Runbook — Deployment (Phase 3 topology)

**Related:** ADR-025 (process topology), scheduler runbook, drainer runbook

## Deploy unit

```
process: api               uvicorn anant.main:app          (HTTP)
process: intake.scheduler  python -m anant.services.intake.scheduler
process: queue.drainer     python -m anant.services.queue.drainer
```

All three run the same code artifact with the same environment; they
differ only in entry point. Production NEVER colocates them.
`ANANT_DEV_MONOPROCESS=1` colocates for local dev only and is ignored
outside `ENVIRONMENT=dev` (hard-stopped in code).

## Required environment

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Postgres, asyncpg driver |
| `JWT_SECRET` | Rotate per Phase 2 drill; never the dev default |
| `INTAKE_KMS_KEY` | ≥32 bytes. Loss orphans all stored intake credentials — see incident runbook. Rotation: Appendix C of PHASE_3_ARCHITECTURE.md |
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REDIRECT_URI` | Gmail OAuth; callback URI pinned per environment |
| `ENVIRONMENT` | `dev` / `staging` / `prod` |
| Tuning (optional) | `SCHEDULER_TICK_SECONDS`, `SCHEDULER_PER_KIND_CONCURRENCY`, `DRAINER_BATCH_SIZE`, `MANUAL_INGEST_PER_MINUTE` |

## Deploy order

1. **Migrate:** `alembic upgrade head` (currently `0003_phase3_wave_f`).
   Migrations are additive; old code runs against the new schema.
2. **Restart `queue.drainer`** — safe at any moment (at-least-once
   delivery; undelivered rows re-selected on boot).
3. **Restart `intake.scheduler`** — safe at any moment (cursors only
   advance on completed syncs; interrupted syncs resume from the last
   committed cursor).
4. **Roll `api`** — API restarts do not pause sync or delivery (CR-7's
   whole point).

Worker restarts cost only latency, never data: the outbox is the source
of truth for undelivered events, the cursor column for sync progress.

## Post-deploy verification

- `GET /v1/health` → 200.
- Logs show `scheduler.started` and `drainer.started` with expected config.
- `SELECT count(*) FROM outbox_events WHERE delivered_at IS NULL` trending
  to zero.
- One `scheduler.tick` with `dispatched > 0` within the longest
  fetch interval (≤30 min), assuming any enabled sources exist.
- Feature flags: all `ff_intake_*` default OFF; per-cohort rollout flips
  per-workspace overrides, never the global default.

## Rollback

Code rollback: redeploy the previous artifact — workers are
restart-safe in both directions. Schema rollback: `alembic downgrade -1`
only if the migration being reverted shipped in the same release and
nothing has written to its tables; otherwise roll forward.
