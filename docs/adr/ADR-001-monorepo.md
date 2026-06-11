# ADR-001 — Monorepo with pnpm workspaces

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

We need to ship a React Native mobile app, a Python backend, and a shared contract layer that both consume. Two viable repository shapes exist: polyrepo (one repo per app + one per shared package) and monorepo (everything in one repo with workspace tooling).

The two failure modes that cost the most engineering time on cross-language products are (1) silent type drift between frontend and backend and (2) cross-cutting changes that span multiple repos and must be coordinated.

## Decision

We use a **single monorepo** managed by **pnpm workspaces**. The Python backend lives alongside the JS apps; pnpm doesn't manage Python dependencies, but `package.json` per workspace gives us a uniform place to declare `lint`, `type-check`, and `test` scripts that pnpm runs in parallel.

We do **not** adopt Nx or Turborepo yet — Phase 1 has only two apps and the orchestration value is below the configuration cost. Turborepo gets added the first time CI exceeds 5 minutes.

## Consequences

**Positive**

- Shared types live in one place; FE/BE drift is impossible by construction (caught by CI drift check)
- Cross-cutting refactors land in one PR
- One lint config, one TypeScript base, one Python style guide for everyone

**Negative**

- All checkout/CI cost is global until we add caching
- Contributors need pnpm installed even to read code

**Revisit when**

- Backend engineering grows past ~10 people, or
- CI runs cross five minutes consistently

## Alternatives considered

- **Polyrepo** — rejected; type drift is the single most expensive class of bug we'd inherit
- **Monorepo with Nx** — premature for two apps; adopt only if scale demands
