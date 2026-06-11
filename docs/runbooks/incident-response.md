# Runbook — Intake Incident Response

**Related:** all Phase 3 runbooks; §17 security model

## Severity guide

| Sev | Examples |
|---|---|
| SEV-1 | Credential exposure suspected; cross-workspace data visible; `INTAKE_KMS_KEY` lost or leaked |
| SEV-2 | All intake stalled (scheduler/drainer down > 30 min); outbox backlog growing unbounded |
| SEV-3 | One provider kind failing fleet-wide (vendor outage); mass `auth_required` event |

## SEV-1 — credential exposure suspected

1. Rotate `INTAKE_KMS_KEY` immediately per Appendix C of the architecture
   (dual-key deploy → batched re-encrypt → drop old key). The re-encrypt
   CLI is idempotent; re-run on failure.
2. If specific Gmail grants may be exposed: revoke upstream now —
   `POST /v1/intake/oauth/gmail/disconnect/{source_id}` per source, or
   Google security console for bulk. Sources flip to `auth_required`;
   users reconnect.
3. Audit trail: `intake_audit_log` (connects/disconnects/refresh
   failures) + structured logs (`oauth.*` events carry account_id,
   workspace_id, source_id — sender addresses are domain-redacted, bodies
   never logged).
4. If `INTAKE_KMS_KEY` is *lost* (not leaked): stored credentials are
   unrecoverable by design. Mark all gmail/api_pull sources
   `auth_required` and notify users to reconnect. No data loss — only
   re-consent.

## SEV-2 — intake stalled

1. `ps`/supervisor: are `intake.scheduler` and `queue.drainer` alive?
   Restart is always safe (see their runbooks).
2. DB reachable? Both workers fail loudly on connection loss and are
   crash-safe; supervisor should auto-restart.
3. Backlog drain check:
   `SELECT count(*) FROM outbox_events WHERE delivered_at IS NULL;` —
   falling after restart means recovered; rising means a subscriber or DB
   problem (drainer runbook).
4. Catch-up after long stalls is automatic: scheduler picks oldest-due
   first; Gmail cursors older than ~7 days self-heal via CR-5 fallback
   (watch for `gmail_history_expired` audit entries — expected, not an
   error).

## SEV-3 — "Gmail auth lapsed" mass event

Trigger: vendor-side token invalidation (Google security sweep, OAuth app
misconfig) flips many sources to `auth_required` at once.

1. Confirm scope: `SELECT count(*) FROM intake_sources WHERE status =
   'auth_required' AND kind = 'gmail';` and check `auth_lapsed` audit
   entries clustering in time.
2. Check the OAuth app first (credentials validity in Google console,
   redirect URI, consent screen status). If the app is broken, fixing it
   plus user reconnects is the only path — there is deliberately no
   server-side way to mint new grants (ADR-023 posture).
3. Sources in `auth_required` are never auto-retried (by design); they
   resume on user reconnect. Mobile surfaces the state as "Auth lapsed"
   with a reconnect path.
4. Comms: this is user-visible. Notify affected workspaces before they
   discover it.

## What does NOT need an incident

- Single source `degraded` — circuit breaker + hourly probe self-heal.
- Dead-letter entries trickling in — ops-inbox workflow (dead-letter
  runbook), not an incident, unless the same error floods.
- `gmail.fallback_recoveries` ticking occasionally — CR-5 doing its job.
  Investigate only if one source recovers perpetually (its sync interval
  may exceed Gmail's ~7-day history horizon).
