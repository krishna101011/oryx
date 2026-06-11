# ADR-004 — Three-Bucket State Management

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

React Native state lives in three places that are easy to conflate: global app state (auth, theme), server state (fetched data with caching needs), and local UI state (form inputs, modal open/closed). Mixing them is the most common cause of unpredictable RN apps — re-render storms, cache invalidation bugs, and "single source of truth that's actually three sources."

## Decision

Three buckets, three tools, one rule per bucket:

| Bucket | Tool | Examples |
|---|---|---|
| Server state | **React Query** | items, drafts, verifications, notifications |
| Global app state | **Redux Toolkit** | auth session, current user, theme, feature flags |
| Local UI state | `useState` / `useReducer` | form inputs, modal open/closed |

Code review rejects:
- Fetched data stored in Redux
- Form input stored in Redux
- Context used for frequently-updated state

## Consequences

**Positive**

- Each tool is excellent at its bucket and avoided where it's bad
- Audit traceability via Redux DevTools matters for Phase 4 verification flows
- React Query owns cache invalidation; we never write it ourselves

**Negative**

- Two libraries instead of one (Zustand would be smaller but worse at audit traceability)

**Revisit when**

- A future phase introduces a workflow where audit traceability of Redux isn't worth the boilerplate

## Alternatives considered

- **Zustand only** — rejected; loses Redux DevTools and time-travel debugging
- **Redux for everything** — rejected; server-state caching in Redux is a documented anti-pattern
- **MobX** — rejected; team familiarity, ecosystem
