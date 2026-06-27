# ADR-046 — Phase 5 → Phase 6 Boundary

**Status:** Accepted — implemented in Phase 5 Wave D
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-030 (research packet as Phase 5 handoff), ADR-029 (intelligence object as Analyze/Research boundary), ADR-014 (event architecture), ADR-018 (outbox pattern)

---

## 1. Context

Every phase boundary in ORYX is a single event, not a shared table read. Phase 4
hands Phase 5 the `research.packet.ready` event (ADR-030); Phase 3 hands Phase 4
the intelligence object (ADR-029). Phase 6 (distribution / analytics — the next
phase) needs to know when content has actually been published to the world. The
decision is what that handoff looks like, so Phase 6 can be built without ever
reaching into Phase 5's internals and so Phase 5 can evolve its schema freely.

## 2. Decision

**`content.published` is the single boundary event. Phase 6 subscribes to it and
must never read Phase 5's tables directly.**

Verified against `services/publishing/engine.py` — the emitted payload is exactly:

| field | source |
|---|---|
| `draftId` | the published draft |
| `publicationId` | the `publications` row that recorded delivery |
| `targetId` | the publish target delivered to |
| `channel` | the channel type (e.g. `webhook`, `twitter_x`) |
| `externalId` | the destination's own id for the post (nullable) |
| `workspaceId` | the owning workspace |

The event is enqueued on the outbox (ADR-018) in the **same transaction** that
marks the publication `delivered`, so "delivered" and "the boundary event exists"
are atomic. It carries `causationId` chaining back to `content.draft.approved`
(itself chained to `content.draft.updated`/`created`) — the full causation chain
is walkable through `outbox_events`, proven end-to-end by
`test_phase5_full_pipeline.py`.

**The payload deliberately carries ids and the channel name only — no draft
content, no credentials, no external URL secrets** (consistent with ADR-041's
write-only credential rule). A subscriber that needs the prose fetches it through
a Phase 5 read API by `draftId`; the event is a notification, not a data dump.

**Phase 6 must never read `content_drafts`, `draft_versions`, `publications`, or
`calendar_entries` directly.** It subscribes to `content.published` and, where it
needs more, calls Phase 5's public read endpoints. This keeps Phase 5's storage
private and the boundary contract explicit.

## 3. Consequences

### Positive
- One event, one contract: Phase 6 can be developed and tested against a single
  payload shape without any knowledge of Phase 5's schema.
- Atomic emit-on-deliver means Phase 6 never sees a "published" signal for a
  delivery that didn't commit.
- The causation chain makes the whole pipeline auditable from one published event
  back to the draft's creation.

### Negative
- A notification-only event means Phase 6 does a follow-up read for content it
  needs. Accepted: it keeps payloads small and storage private, and most Phase 6
  use cases (analytics, distribution tracking) need only the ids.
- The contract is enforced by convention + review, not by a physical access
  boundary. Mitigated by this ADR and the repository pattern (ADR-006); a future
  service split could make it physical.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Phase 6 reads Phase 5 tables directly | Freezes Phase 5's schema as a public API; any change risks breaking Phase 6 silently. |
| Put full draft content in the event payload | Bloats the outbox, risks leaking content into logs/replays, and duplicates the source of truth. |
| Multiple boundary events (published, failed, scheduled, …) for Phase 6 | Over-specifies the boundary; Phase 6's trigger is "content went live" — one event. Internal lifecycle events stay internal. |
| Synchronous call from Phase 5 into Phase 6 | Couples publishing latency/availability to a downstream phase; the outbox event decouples them. |
