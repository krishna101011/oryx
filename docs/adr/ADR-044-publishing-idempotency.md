# ADR-044 — Publishing Idempotency

**Status:** Accepted — implemented in Phase 5 Wave D
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-040 (channel adapter protocol), ADR-045 (content calendar scheduler), ADR-018 (outbox pattern)

---

## 1. Context

Publishing is the one irreversible step in the phase: once a tweet is posted or an
email is sent, it cannot be un-sent. The engine is invoked from several paths —
the publish API, the calendar scheduler firing a scheduled entry, and the
scheduler's transient-retry re-drive — and the outbox/retry machinery can call any
of them more than once. Without a hard guarantee, a redelivery or a concurrent
call would double-post. "We check a flag first" is not strong enough under
concurrency; the guarantee has to be structural.

## 2. Decision

**`UNIQUE(draft_id, version_number, target_id)` on `publications`
(`uq_publications_draft_version_target`, migration 0012) is the actual
database-level idempotency guarantee. The engine checks for an existing
`delivered` row before it ever calls an adapter.**

Verified against `services/publishing/engine.py`:

- **Pre-adapter short-circuit.** In `_publish_one`, before any network call, the
  engine reads the publication for `(draft, version, target)`. If one exists with
  status `delivered`, it returns that result immediately and the adapter is
  **never** called again (§16.2).
- **Race-safe pending insert.** It then `ensure_pending(...)` inserts the pending
  row **ON CONFLICT DO NOTHING** against the unique constraint, commits, and
  re-reads the winner. Concurrent callers therefore converge on one row; if a
  competitor delivered in the gap between check and insert, the re-read sees
  `delivered` and returns without calling the adapter.
- **The constraint is the contract, not the check.** The application check is an
  optimization that avoids a wasted adapter call in the common case; correctness
  under concurrency comes from the unique index. Idempotency is structural.
- **Per-target independence.** Fan-out delivers each target in its own atomic
  unit, so one target's failure never rolls back another's delivered row, and
  re-publishing to a *new* target after a partial success works (the draft-status
  guard accepts `approved`/`published`/`scheduled` for exactly this reason).

On success the engine marks the row `delivered` and emits `content.published`
(ADR-046) in the same transaction; on permanent failure it marks `failed`; on
transient failure below the ceiling it leaves the row `pending` for re-drive
(ADR-045), advancing `attempt_count`.

## 3. Consequences

### Positive
- Double-posting is impossible by construction, even under concurrent invocation
  or event redelivery — the irreversibility of publishing is matched by a
  structural guard.
- Every entry path (API, calendar fire, retry re-drive) shares one idempotent
  function; no path needs its own dedupe logic.
- The pre-adapter check keeps the happy path cheap (no redundant network call).

### Negative
- Idempotency is keyed on `(draft, version, target)`, so a *new* draft version
  republished to the same target is a distinct, allowed delivery. This is the
  intended semantics (a new version is new content), but it means "don't publish
  the same target twice" holds per-version, not per-draft.
- ON CONFLICT DO NOTHING + re-read is two round-trips on the insert path.
  Accepted: it is the price of race-safety and only the pending insert pays it.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Application-level "have we delivered?" check only | Loses to a concurrent caller between check and insert; produces a double-post under exactly the redelivery the outbox can cause. |
| Idempotency key generated per request | Reinvents what `(draft, version, target)` already uniquely identifies; adds a key to thread through every path. |
| Advisory lock around publish | Serializes delivery and adds a failure mode (lock holder dies); the unique constraint gives the guarantee without a lock. |
| Key idempotency on `(draft, target)` ignoring version | A legitimately new version could never be republished to the same target; version is part of the content identity. |
