# Guide — Intake Troubleshooting

**Audience:** engineers and operators debugging "my source isn't working"
**Related:** scheduler/drainer runbooks; §10 retry model; §5/§4/§6/§7 provider designs

## First three checks, always

1. **Source row:** `SELECT status, enabled, consecutive_failures,
   last_error, last_attempt_at, last_synced_at FROM intake_sources WHERE
   id = :id;`
2. **Audit trail:** `SELECT event, data, created_at FROM intake_audit_log
   WHERE intake_source_id = :id ORDER BY created_at DESC LIMIT 20;`
   (also visible in mobile → Source detail → View activity)
3. **Workers alive:** `scheduler.started` / `drainer.started` in recent logs.

## Decode the status

| status | Meaning | Path out |
|---|---|---|
| `healthy` | Syncing on its interval | — |
| `degraded` | Circuit open (10 consecutive failures) or permanent-class error | Hourly probe auto-recovers once the cause clears; force a probe by clearing `last_attempt_at` |
| `auth_required` | Credentials invalid; never auto-retried | User reconnects (Gmail OAuth / new API key). Operator cannot fix server-side — by design |
| `disabled` | Soft-disabled (user, operator, or CR-6) | PATCH `enabled=true` if intentional re-enable |

## Per-provider quirks

**RSS**
- `304` ticks `last_synced_at` without items — healthy, not a bug.
- Permanent redirect (301): the new URL is persisted on BOTH the
  operational config and the originating custom-source row, the cursor is
  cleared, and an `rss_permanent_redirect` audit entry is written; the
  next tick re-pulls fresh. A 302 is followed once and never persisted.
- Repeated `degraded` with parse errors in `last_error`: fetch the feed
  by hand; many "RSS" URLs are HTML pages.

**Gmail**
- `gmail_history_expired` audit entry = CR-5 recovery ran (cursor older
  than Gmail's ~7-day history window). One-off after downtime: normal.
  Recurring on one source: its effective sync gap exceeds the horizon —
  investigate why it isn't being scheduled.
- Bootstrap pulls are capped at 200 messages; older mail than the
  configured lookback is intentionally not ingested.
- `auth_required` right after connect: check granted scopes — exchange
  refuses grants that don't include `gmail.readonly` (ADR-023).

**Webhook**
- Vendor reports deliveries failing: signature (HMAC over the *raw*
  body), timestamp within ±5 min (clock skew!), idempotency key present.
  401/403 → signature or window; 429 → per-source rate limit (60/min);
  413 → 256 KiB body cap.
- "Vendor retried and you dropped it": that's the idempotency table doing
  its job — the first delivery was accepted.
- Secret lost: rotate (old secret stays valid 24h) — secrets are stored
  hashed and cannot be re-displayed.

**API pull**
- `degraded` with SSRF errors in `last_error`: the target resolved to a
  private/link-local/metadata address. The deny-list is not configurable
  per-source — by design (§17.1).
- Endless pagination: per-sync page cap is 20 per endpoint; vendors that
  never exhaust should get a tighter `fetch_interval_minutes`.

## "Item didn't show up"

1. Provider-key dedupe? Same `(source, external_id)` is silently skipped.
2. Fingerprint dedupe? Check `intake_items_duplicates` /
   `dedupe_skip` audit entries — cross-source duplicate collapsed into the
   first sighting (ADR-019). Body-only items additionally bucket by day.
3. Actually ingested but you're looking for content in mobile? Phase 3
   deliberately has **no item list UI** (§15.3) — verify in DB:
   `SELECT * FROM intake_items WHERE intake_source_id = :id ORDER BY
   fetched_at DESC LIMIT 5;`

## "Event didn't reach the subscriber"

Outbox row exists? → drainer runbook. Row delivered but no effect? →
subscriber-side idempotency may have absorbed a replay (correct), or the
handler failed and is retrying (check `attempts`/`last_error`). Row in
dead-letter? → dead-letter recovery runbook.
