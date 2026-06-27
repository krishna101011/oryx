# ADR-043 — Packet Consumption Semantics

**Status:** Accepted — implemented in Phase 5 Wave A
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-030 (research packet as the Phase 5 handoff), ADR-039 (draft version control), ADR-018 (outbox pattern)

---

## 1. Context

Phase 4 hands Phase 5 a research packet via the `research.packet.ready` event
(ADR-030). Two questions follow. First: what does "Phase 5 received this packet"
mean, concretely and idempotently, given the event can be redelivered? Second:
does receiving a packet *automatically* produce a draft, or is drafting a
separate, deliberate act? Getting this boundary wrong either double-consumes
packets on redelivery or surprises analysts with AI content they never asked for.

## 2. Decision

**`consumed_at` is set exactly once, idempotently, by `PacketConsumerHandler` on
`research.packet.ready`. Draft generation is a separate, manual, analyst-triggered
step. One draft per packet, enforced by a UNIQUE constraint.**

Verified against the code:

- **Consumption marks `consumed_at` and nothing else.** `PacketConsumerHandler`
  (subscriber registered in `build_bus()`) calls `DraftService.consume_packet`,
  whose entire job is to set `research_packets.consumed_at`. It does **not** set
  packet `status`, and it does **not** generate a draft. This is **invariant #2**
  of the Wave A contract.
- **Idempotent.** `consume_packet` returns early if the packet is already consumed
  (`consumed_at is not None`) — redelivery is a no-op. If the workspace was
  deleted it dead-letters via `PermanentDeliveryError`; if the packet was
  cascade-deleted it returns quietly.
- **Generation is manual.** A draft is created only by an explicit analyst action,
  `POST /v1/drafts/generate` → `DraftService.generate_draft`. (That path *also*
  calls `mark_packet_consumed` idempotently, so generating from a still-unconsumed
  packet is safe whether or not the handler ran first.)
- **One draft per packet — structural.** `content_drafts` has UNIQUE
  `(workspace_id, packet_id)` (migration 0009). `generate_draft` checks for an
  existing draft and returns it unchanged; the constraint backs that against a
  race (a lost insert returns the winner's draft). Application logic *and* the DB
  agree.

## 3. Consequences

### Positive
- A clean, single-writer boundary: Phase 5 owns `consumed_at`, sets it once, and
  redelivery never double-acts.
- Analysts are never surprised by auto-generated content; drafting is a chosen
  act with chosen format/instructions.
- One-draft-per-packet is guaranteed by the schema, not merely hoped for in code.

### Negative
- Two code paths can set `consumed_at` (the handler and `generate_draft`). Both
  are idempotent, so this is safe, but it is two places to keep honest. Accepted:
  it makes "generate works even if the handler hasn't run yet" true without
  ordering assumptions.
- "Manual generation" means a ready packet can sit un-drafted indefinitely.
  Intended: that is the analyst's call, and `/me`'s `readyPacketCount` surfaces
  the backlog.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Auto-generate a draft on `packet.ready` | Surprises analysts with unrequested AI content and spends budget without intent; drafting is an editorial decision. |
| Enforce one-draft-per-packet in app logic only | A race could create two drafts; the UNIQUE constraint makes it impossible, not just unlikely. |
| Set packet `status='consumed'` from the handler | Overloads Phase 4's status field across the phase boundary; `consumed_at` is Phase 5's own single marker and leaves status to Phase 4. |
| Make consumption non-idempotent (assume single delivery) | The outbox can redeliver; a non-idempotent handler would double-consume. |
