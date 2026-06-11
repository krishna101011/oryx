# ADR-003 — FastAPI over Django

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

The backend must be API-first. It will eventually host AI-streaming workloads (Phase 4), real-time integration listeners (Phase 3+), and a verification engine that runs many small inference calls per request. The two mature Python options are Django (batteries-included) and FastAPI (async-first, pydantic-everywhere).

## Decision

Use **FastAPI** with **Pydantic v2** for every request and response model. Django's strengths (admin panels, ORM, templates) are batteries we don't need; its synchronous request lifecycle would be a liability for Phase 4 workloads.

## Consequences

**Positive**

- Async-first matches the workload profile of later phases
- Pydantic models double as the source for auto-generated OpenAPI
- The pydantic mirror of `shared-types` lands cleanly in this stack
- Minimal magic — every route is explicit

**Negative**

- No built-in admin panel; we'll build a thin internal tool later
- ORM is our choice (SQLAlchemy 2.0 likely, decided in Phase 2)

**Revisit when**

- We hit a performance ceiling that requires switching to Rust-based services for hot paths

## Alternatives considered

- **Django + DRF** — rejected; sync-first model doesn't fit the AI workloads
- **Flask + Marshmallow** — rejected; less ergonomic for async and lacks the OpenAPI tightness
- **Node/NestJS** — rejected; we want Python on the ML-adjacent side
