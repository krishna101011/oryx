# ADR-014 — Event Architecture

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 2 (contract only); first real usage Phase 4
**Supersedes:** none
**Related:** ADR-015 (provider layer)

---

## 1. Context

Every later phase of ORYX is event-driven:

- Phase 3 emits `intake.item.received` when Gmail / RSS / webhooks deliver
- Phase 4 emits `item.verified`, `item.analyzed`, `item.clustered`
- Phase 5 emits `draft.created`, `draft.published`
- Phase 6 emits `alert.scheduled`, `alert.delivered`, `digest.compiled`
- Phase 7 reads every event for analytics

If we let each phase invent its own event mechanism, we will end up with five incompatible bus implementations and a year of cleanup work. This ADR locks in the event architecture now, before Phase 3 starts.

We must answer four questions:

1. When is a call synchronous, and when is it an event?
2. How are async events delivered?
3. What does a domain event look like?
4. How does the system evolve from in-process to distributed?

---

## 2. Decision

### 2.1 Two Classes of Inter-Service Communication

We distinguish two communication patterns. Mixing them is the most common cause of brittle systems.

#### Sync events (commands / queries)

Caller needs a result *now* before continuing.

- Same-request, same-process, function call
- Return value is the contract
- Caller knows the callee
- Used for: read paths, validation, atomic transactional work

Example: `auth_service.create_session(account_id)` — the signup endpoint cannot return until the session exists. This is a sync call, not an event.

#### Async events (domain events / notifications)

Something happened. Anyone who cares can react. The emitter does not wait.

- Fire-and-forget from emitter's perspective
- Zero or many subscribers
- Emitter does not know who subscribes
- Used for: side effects, downstream pipelines, audit, analytics

Example: when an intake item arrives, `intake.item.received` is emitted. Verification subscribes. Analytics subscribes. The intake service does not call either of them by name.

#### Decision rule

If the caller's response correctness depends on the callee succeeding, it is a **sync call**.
If the system would still be correct (just less timely) without the callee, it is an **async event**.

### 2.2 Domain Event Shape

Every async event in the system uses one canonical envelope:

```ts
interface DomainEvent<TName extends string, TPayload> {
  id: string;                  // uuid v7 (time-sortable)
  name: TName;                 // 'intake.item.received', 'item.verified', ...
  version: 1;                  // event schema version, bumped on breaking changes
  occurredAt: string;          // ISO 8601, when the fact became true
  emittedAt: string;           // ISO 8601, when it left the emitter
  workspaceId: string | null;  // data-scope key; null only for platform events
  actor: {                     // who/what caused this
    kind: 'account' | 'system' | 'provider';
    id: string | null;
  };
  correlationId: string;       // ties multi-step flows together; defaults to request id
  causationId: string | null;  // the event id that caused this one (for tracing chains)
  payload: TPayload;           // event-specific data; typed in shared-types
}
```

Reasoning:

- `id` lets consumers dedupe on at-least-once delivery
- `version` lets producers evolve payload shape without breaking subscribers
- `workspaceId` makes per-tenant routing and isolation trivial
- `correlationId` + `causationId` together let us reconstruct full causal chains in observability tools
- `payload` is event-specific and lives in `packages/shared-types/events/`

### 2.3 Event Naming Convention

`<domain>.<entity>.<verb_past_tense>`

Examples: `intake.item.received`, `auth.session.created`, `verification.item.verified`, `publishing.draft.published`.

Rules:

1. Past tense — events report facts, not requests
2. One dot-separated namespace per emitting service
3. Names are immutable once shipped; renaming requires a new event name

### 2.4 Queue Strategy — Phased Adoption

Distributed event infrastructure is a maintenance liability we earn the right to take on. We adopt it in three stages:

| Stage | When | Implementation | Where state lives |
|---|---|---|---|
| **Stage A** — In-process bus | Phase 2 → end of Phase 3 | Python `EventBus` interface + `InProcessBus` impl using `asyncio.Queue` per subscriber | Process memory; restart loses unprocessed events (acceptable: intake is idempotent, replays from source) |
| **Stage B** — Persistent outbox | Phase 4 | Same `EventBus` interface + `OutboxBus` impl: events written transactionally to an `outbox_events` DB table, drained by a background worker | DB; survives restarts |
| **Stage C** — External broker | Phase 6 or when service count > 1 | `EventBus` impl backed by Redis Streams or NATS JetStream | Broker; multi-consumer fan-out, replay, cross-service |

The **`EventBus` interface is stable across all three stages**. Service code never changes when we swap implementations.

```python
# illustration only — Phase 2 documents the interface; Phase 3 ships the in-process impl
class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, name: str, handler: Callable[[DomainEvent], Awaitable[None]]) -> None: ...
```

Why this matters: every service is written against `EventBus`. Swapping `InProcessBus` for `OutboxBus` in Phase 4 is a one-line change in `main.py`'s startup wiring. No service code moves.

### 2.5 Delivery Guarantees

We commit to **at-least-once** delivery from the start. Handlers must be idempotent.

- Stage A (in-process): exactly-once *within a process lifetime*; lost on restart
- Stage B (outbox): at-least-once across restarts; retries on failure with exponential backoff
- Stage C (broker): at-least-once with consumer-group semantics; ordering per partition only

We do **not** promise exactly-once delivery. Building on that promise is how distributed systems get expensive. Idempotent handlers are cheap; transactional dedup is not.

**How idempotency is achieved:**

- Handlers store `processed_event_ids` (event id, handler name) and check before acting
- For derived data, prefer upserts keyed on the event's payload identifier
- For external side effects (a vendor API call), use an idempotency key derived from `event.id`

### 2.6 Pub/Sub Topology

```
  ┌────────────────┐
  │  EMITTER       │  publish(DomainEvent)
  │  (any service) │
  └───────┬────────┘
          │
          ▼
  ┌───────────────────┐
  │     EventBus      │  routes by event.name
  └─┬─────────┬───────┘
    │         │
    ▼         ▼
  ┌─────┐   ┌─────┐
  │ Sub │   │ Sub │   N subscribers per event name
  └─────┘   └─────┘
```

Rules:

- Subscribers register at service startup, never inside request handlers
- A subscriber that fails does NOT block other subscribers
- A subscriber that throws is logged, the failure metric is incremented, and the event is retried per the bus implementation's policy
- Subscribers must complete in < 5 seconds at p99; longer work spawns its own follow-up event

### 2.7 Outbox Pattern (Stage B detail)

When we move to Stage B, every event is published in the same DB transaction that produced the underlying state change. This is the **outbox pattern** — it eliminates the "wrote to DB, crashed before publishing" failure mode.

```
BEGIN TX
  INSERT INTO research_items (...) VALUES (...);
  INSERT INTO outbox_events (event) VALUES (jsonb(...));
COMMIT
```

A background `OutboxDrainer` reads new rows, publishes to subscribers, marks rows as `delivered_at`. Failed deliveries retry with backoff. Rows aged out after retention window.

### 2.8 What is NOT Allowed

- Service code calling another service's handler directly — must go through the bus or a sync interface
- Emitting an event from within another event's handler **without** setting `causationId` to the parent event's id
- Cross-workspace event handlers — every handler must scope on `workspaceId`
- Synchronous event handlers blocking the request path — emit, then return

---

## 3. Consequences

### 3.1 Positive

- Phase 3 ships intake against a stable bus interface
- Phase 4 can add the outbox without touching Phase 3 code
- Phase 6 can move to an external broker without touching Phase 3 or Phase 4
- Observability gets correlation chains for free
- Adding analytics (Phase 7) is "subscribe to everything"
- Vendor migrations (broker swaps) are isolated to one file

### 3.2 Negative

- One extra abstraction every developer must understand
- Idempotency is a discipline that lapses easily — every handler PR needs review for it
- Stage A's in-process bus *will* drop events on a crash; we accept this because intake is replayable

### 3.3 Migration Path

| When | What we do |
|---|---|
| Phase 2 | Ship `EventBus` interface + `InProcessBus` impl + the event envelope type |
| Phase 3 | First real emitters (intake), first real subscribers (in-process) |
| Phase 4 (start) | Add `outbox_events` table; switch `main.py` to `OutboxBus`; existing handlers unchanged |
| Phase 6 or earlier as load demands | Add Redis Streams / NATS broker; switch `main.py` to `BrokerBus`; handlers still unchanged |

The bus interface is the seam. Implementations come and go behind it.

### 3.4 Open Questions (deferred, not blocking)

- Choice between Redis Streams vs NATS JetStream for Stage C — defer to when that stage is imminent
- Whether we need a separate audit topic with longer retention — likely yes; revisit in Phase 7
- Schema registry tooling — likely overkill until we have multiple services; revisit when Stage C lands

---

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Direct service-to-service calls everywhere | Tightens coupling; every new subscriber requires editing the emitter |
| Adopt Kafka / NATS in Phase 2 | Infrastructure burden with no Phase 2 consumers; classic premature optimization |
| Choose one bus impl now and stick with it | Stage A is the wrong choice for production; Stage C is the wrong choice for Phase 2. Phased adoption matches reality |
| Use FastAPI background tasks instead of a bus | No fan-out, no retry, no introspection; fine for fire-and-forget tasks, wrong for domain events |
| At-most-once delivery | Loses events on transient failures; intelligence products especially can't afford this |

---

## 5. Enforcement

- Lint rule: no service may import another service's module directly except via its public interface
- Code review: every new event addition requires a `payload` type in `shared-types/events/` and an entry in the event catalog (docs)
- Tests: every handler has an idempotency test (handle the same event twice, assert no double effect)
- CI: bus impl swap is exercised in integration tests (both `InProcessBus` and `OutboxBus` once Stage B lands)

---

*This ADR is the event-architecture contract. Any later phase that needs a new pattern updates this ADR or supersedes it; no shadow implementations.*
