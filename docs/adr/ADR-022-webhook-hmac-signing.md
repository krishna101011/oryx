# ADR-022 — Webhook HMAC Signing, Timestamp Window, Idempotency

**Status:** Accepted
**Date:** 2026-06-11
**Phase introduced:** 3
**Related:** ADR-021 (credential encryption), ADR-018 (outbox)

---

## 1. Context

`POST /v1/intake/webhooks/:workspace_id/:intake_source_id` is the only
unauthenticated write surface in the product — vendors cannot hold bearer
tokens. Its security must come entirely from the request itself. Three
distinct attacks need three distinct controls: forgery, replay of a
captured request, and duplicate delivery from a well-behaved retrier.

## 2. Decision

Three independent controls, all required:

| Control | Header | Defeats |
|---|---|---|
| HMAC-SHA256 over the raw body | `X-Anant-Signature` | Forgery — only holders of the per-source secret can produce it |
| ±5-minute timestamp window | `X-Anant-Timestamp` | Replay of a previously valid request |
| Idempotency key, 24h TTL | `X-Anant-Idempotency-Key` | Duplicate delivery (vendor retries) |

Secret lifecycle:

- Per-source secret generated server-side at connect time; displayed to
  the user **once**; stored hashed (never recoverable from our DB).
- Rotation issues a new secret and honors the old one for a 24-hour grace
  window so vendors can cut over without dropped deliveries.

Idempotency keys persist in `webhook_idempotency_keys` (CR-4) — a DB
table, deliberately not process memory, so a restart cannot reopen the
dedupe window. The scheduler purges expired keys hourly. Body size is
capped at 256 KiB and per-source rate limits apply (60 req/min default);
both are enforced in-app, never delegated solely to the edge.

## 3. Consequences

### Positive
- Each control is independently testable (unit: signature verify, window
  math, TTL purge; integration: replay + duplicate paths).
- A leaked request log does not enable replay (window) or re-submission
  (idempotency), and never reveals the secret (hashed at rest).

### Negative
- Vendors must implement signing — `generic_json` config keeps the
  template mapping simple, but the signature step is non-negotiable.
- Clock skew beyond ±5 minutes rejects legitimate deliveries (accepted;
  surfaced in the troubleshooting runbook).

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Static bearer token per source | Replayable forever if leaked; no integrity over the body |
| Signature only, no timestamp | Captured request replays indefinitely |
| In-memory idempotency cache | Restart resets the window — the exact footgun CR-4 removed |
| IP allowlisting | Vendor IPs churn; operationally brittle and not an integrity control |
