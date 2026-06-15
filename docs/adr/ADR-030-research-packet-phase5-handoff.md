# ADR-030: Research Packet as the Phase 5 Handoff

**Status:** Accepted
**Date:** 2026-06-15
**Phase:** 4

## Context

Phase 4 (Verify · Analyze · Research) ends where content generation (Phase 5)
begins. We need exactly one, well-defined boundary object so the two phases are
not coupled through shared tables or implicit reads. That boundary must also
let an analyst assemble a deliberate, gated bundle of intelligence — not a raw
dump — and it must be safe against publishing contested material by accident.

## Decision

The **research packet** is the only object that crosses the Phase 4 → Phase 5
boundary. An analyst curates intelligence objects into a research workspace,
then assembles a packet from them. The boundary event is
`research.packet.ready` (`services/research/events/constants.py`); **Phase 5
subscribes to this event and nothing else from Phase 4.**

A packet may only move to `ready` if its **readiness gate** passes
(`packet_assembler.py`, enforced at the API layer with **HTTP 409**, not just
in the UI): no constituent object may be `analyst_rejected`, and any
`contested` object must appear in the packet's `conflict_acknowledged_ids` —
i.e. **a contested object requires explicit analyst acknowledgement** before it
can ship.

`consumed_at` marks the packet as taken by Phase 5 and **is set exclusively by
Phase 5**. No Phase 4 code path writes `consumed_at`. A packet is effectively
**immutable once consumed** — Phase 4 neither reads nor mutates a consumed
packet.

## Consequences

- **Positive:** Phase 5 has a single, typed subscription point and never reaches
  into claims, evidence, conflicts, or intelligence objects directly. The phases
  can evolve independently behind the packet contract.
- **Positive:** the gate makes "publish a rejected or unacknowledged-contested
  object" structurally impossible, and the gate is server-enforced so a rogue
  client cannot bypass it.
- **Negative:** `consumed_at` ownership is a convention the codebase enforces by
  discipline (and tests), not by a database permission boundary; a future Phase
  5 bug could in principle write it early. The acknowledgement step adds analyst
  friction for contested objects (by design).

## Alternatives Considered

- **Phase 5 reads intelligence objects directly.** Rejected: couples the phases,
  removes the gate, and gives Phase 5 access to un-curated, possibly contested
  material.
- **Auto-ready packets when all objects are verified.** Rejected: assembly is a
  deliberate analyst act; auto-ready would publish whatever happened to verify,
  not what the analyst chose.
- **Let Phase 4 set `consumed_at` when it emits `packet.ready`.** Rejected:
  "ready" and "consumed" are different facts owned by different phases; conflating
  them would make the handoff lossy and untraceable.
