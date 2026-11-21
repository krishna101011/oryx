# Runbook — Deployment

**Scope:** Current ORYX backend process topology and deployment sequence.

**Related:** ADR-025 (process topology), `docs/SECURITY.md`, `docs/DEV_SETUP.md`

This runbook describes the process entry points present in `apps/backend/src/oryx/main.py` and the standalone worker modules. It is not a substitute for environment-specific infrastructure configuration (container definitions, ingress, secrets manager, backups, or monitoring).

## 1. Deployment unit and process topology

Deploy the same backend artifact to **six independently managed processes**:

| Process | Command (run from `apps/backend`) | Responsibility |
|---|---|---|
| API | `uv run uvicorn oryx.main:app --host 0.0.0.0 --port 8000` | HTTP API |
| Intake scheduler | `uv run python -m oryx.services.intake.scheduler` | Polls enabled intake sources and runs the intake idempotency-key purge |
| Outbox drainer | `uv run python -m oryx.services.queue.drainer` | Delivers queued events and runs outbox cleanup |
| Calendar scheduler | `uv run python -m oryx.services.calendar.scheduler` | Fires scheduled publications and re-drives eligible transient failures |
| Activity digest worker | `uv run python -m oryx.services.activity.digest` | Builds scheduled activity digests |
| Analytics rollup worker | `uv run python -m oryx.services.analytics.rollup` | Refreshes daily analytics rollups |

Run each command as its own supervised service/process in staging and production. Configure the process manager to restart a process after an unexpected exit and to forward its stdout/stderr to the deployment's log sink.

All processes use the same release artifact and environment-specific configuration. They connect to the same PostgreSQL database. Do not run multiple copies of singleton schedulers/drainers unless the relevant worker has been explicitly designed and validated for concurrent operation.

### Local development exception

The API can colocate all five workers for local development when `ORYX_DEV_MONOPROCESS=1` and `ENVIRONMENT=dev`. The setting is ignored outside `ENVIRONMENT=dev`. Do not use this mode as the production topology.

## 2. Runtime and database requirements

- Python **3.12 or newer** (the backend declares `requires-python = ">=3.12"`).
- Install the backend's locked dependencies with `uv sync` (include `--extra dev` only for development/test environments).
- PostgreSQL reachable by every process.
- The backend database URL must use SQLAlchemy's asyncpg form, for example `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE`.

Run backend commands from `apps/backend`, where `pyproject.toml` and `alembic.ini` are located.

## 3. Environment configuration

Set environment variables through the deployment's secret/configuration manager. Do not commit production secrets to the repository or bake them into an image.

### Core settings

| Variable | Requirement / purpose |
|---|---|
| `ENVIRONMENT` | Set to `staging` or `prod` for those environments. |
| `DATABASE_URL` | PostgreSQL connection URL using the asyncpg driver. |
| `JWT_SECRET` | Set a high-entropy secret. Never use the repository's development placeholder. |
| `CORS_ORIGINS` | Configure the explicit frontend origin allowlist for non-dev environments. |
| `INTAKE_KMS_KEY` | Provide a key of at least 32 bytes wherever intake credentials are stored. Loss of this key can make stored intake credentials unrecoverable; follow the intake-key rotation/incident guidance before changing it. |

### Feature-specific settings

Configure these only when enabling the corresponding integration or delivery path:

- **Gmail intake:** `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, and the environment-specific `GMAIL_REDIRECT_URI`.
- **Publishing target credentials:** `ORYX_PUBLISH_KEY`, a base64-encoded 32-byte key, when encrypted publish-target credentials are used.
- **AI:** `AI_PROVIDER` and the matching provider credentials/settings. The default provider is Anthropic; Ollama and OpenAI-compatible providers have separate settings.
- **Push and alert email:** defaults are `PUSH_PROVIDER=log_only` and `EMAIL_PROVIDER=log_only`. Configure the real provider and its credentials before promising external delivery.
- **Payments:** configure Stripe or Razorpay credentials and webhook secrets before enabling live payment flows.
- **Training video:** configure Cloudflare Stream credentials before enabling provider-backed video operations.

### Worker tuning

Optional settings currently defined by backend configuration include:

- `SCHEDULER_TICK_SECONDS`
- `SCHEDULER_PER_KIND_CONCURRENCY`
- `DRAINER_BATCH_SIZE`

The API and all workers should receive consistent database and shared-secret configuration. Do not put worker-only secrets in frontend/mobile build variables.

## 4. Deployment sequence

Use the following sequence for each release. Adapt the orchestration commands to the hosting platform, but preserve the ordering and checks.

1. **Prepare the release.** Build/publish one immutable backend artifact. Confirm the intended environment variables and secret versions are available to the API and all five workers.
2. **Back up PostgreSQL.** Take or verify a recoverable backup/snapshot according to the database operator's procedure before applying schema changes.
3. **Apply migrations once.** From `apps/backend`, run:

   ```bash
   uv run alembic upgrade head
   ```

   The current repository migration chain ends at `0037_phase9_market_foundation`. Do not pin deployments to an older migration revision; `head` applies the repository's current migration head.
4. **Deploy/restart workers.** Roll out the five worker processes using the commands in Section 1. Ensure each process is supervised and connected to the intended database.
5. **Deploy/restart the API.** Start the API process using the command in Section 1 and route traffic to it only after its health check succeeds.
6. **Verify the release.** Complete the checks in Section 5 and inspect application/worker logs before considering the deployment complete.

Do not assume every migration is backward-compatible merely because earlier migrations were designed to be additive. Review the actual migration in the release and coordinate application/worker rollout when a schema change requires it.

## 5. Post-deployment verification

- **API health:** `GET /v1/health` returns HTTP 200.
- **Process health:** the API and all five workers are running under the process supervisor; none is crash-looping.
- **Startup logs:** inspect each process for its startup event and configuration. The intake scheduler emits `scheduler.started`; the outbox drainer emits `drainer.started`. Also verify startup messages from the calendar scheduler, digest worker, and rollup worker.
- **Database version:** verify Alembic reports the expected current head in the deployed database. The API also performs a startup migration check and warns if the database is behind; that warning is not a replacement for the explicit migration step.
- **Outbox:** inspect the count and age of undelivered `outbox_events`. A non-zero backlog is not automatically a failure, but it should be draining and not growing without explanation.
- **Intake:** where enabled and configured sources exist, confirm scheduler activity and successful syncs within the source's configured fetch interval. No dispatch is expected when there are no due sources.
- **Calendar, digest, analytics:** confirm their worker logs show successful ticks when eligible work/data exists.
- **Integrations:** verify each enabled external provider with its own health/credential check. A provider configured as `log_only` is not delivering externally.
- **Feature flags:** confirm rollout flags are set intentionally for the target workspaces/cohorts before enabling user-facing functionality.

## 6. Rollback and recovery

### Application rollback

If the new application artifact is unhealthy, redeploy the previous known-good artifact to the API and worker processes as a coordinated release. Check the database compatibility of the previous artifact before rolling it back.

### Database recovery

Do not run `alembic downgrade -1` as a generic rollback. A downgrade can destroy data or fail after newer code has written to the changed schema. Before any schema rollback:

1. Identify the exact migration(s) applied by the release.
2. Read their upgrade and downgrade operations.
3. Confirm whether any application/worker has written data using the new schema.
4. Confirm a recoverable backup exists.
5. Prefer a forward-fix migration when data has been written or downgrade safety is uncertain.

If database integrity is in doubt, stop the affected writers/workers and follow the database backup/restore procedure rather than improvising schema changes during an incident.

## 7. Deployment limitations to resolve before production

This runbook documents the current application process topology and configuration surface. It does **not** certify that production infrastructure is ready. Before a production launch, separately verify:

- managed PostgreSQL backups, restore drills, network restrictions, and connection capacity;
- TLS termination, ingress/proxy configuration, and trusted forwarding headers;
- centralized logs, metrics, alerting, and worker-liveness monitoring;
- secret provisioning and rotation for JWT, intake encryption, publishing credentials, and enabled providers;
- deployment-specific process definitions and restart/shutdown behavior;
- a tested release and rollback procedure against a staging environment.
