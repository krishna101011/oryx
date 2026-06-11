# ADR-006 — Defer Database Choice via Repository Pattern

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

Phase 1's job is the foundation. The domain isn't stable enough to commit to a schema — Phase 2 introduces auth and the users domain; Phase 4 introduces research, verification, and clusters. Picking a database now and writing migrations would couple us to schemas before we know the shape.

But we also can't have services with no storage interface — every service folder needs a clear seam for where persistence will plug in.

## Decision

Every service folder ships with a `repository.py` that defines an **abstract storage interface** (Python `Protocol`). Phase 1 has no concrete implementation; services depend on the interface only. Phase 2 lands the concrete implementation — almost certainly Postgres + SQLAlchemy 2.0 async, decided in ADR-008+ when that work begins.

The repository:

1. Translates storage rows into domain models
2. Hides the choice of database from services
3. NEVER makes HTTP calls
4. NEVER contains business rules

## Consequences

**Positive**

- Service code is unaffected when the DB choice is made
- Unit testing services becomes trivial — inject an in-memory fake
- We can change the DB later without rewriting business logic

**Negative**

- One extra layer to traverse for every read/write
- Repository interfaces can drift toward leaky abstractions if not reviewed

**Revisit when**

- Phase 2 — pick the concrete DB and ORM
- Any phase where reads need a different store (search index, vector DB)

## Alternatives considered

- **Pick Postgres now and write the schema** — rejected; coupling to schemas before domain is stable
- **Active Record via models that know how to save themselves** — rejected; mixes persistence and domain logic
