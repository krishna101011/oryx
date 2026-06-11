# ADR-002 — Expo Managed Workflow

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

React Native ships two workflows: bare (you own iOS/Android projects) and Expo managed (Expo owns build infra, OTA updates, native module access). The choice affects how fast we ship, how flexibly we use native code, and how complex our CI becomes.

## Decision

Use **Expo managed**. Over-the-air updates, dev tooling, push notifications, and build pipelines come for free. We can eject to bare if a later phase requires a native module Expo doesn't expose.

## Consequences

**Positive**

- One-command boot for any contributor
- EAS Build replaces Xcode + Android Studio chores
- OTA updates let us patch UI/UX without app-store submission
- Expo's first-class TypeScript and SecureStore align with our Phase 2 plans

**Negative**

- Some native modules are blocked or require a custom dev client
- Build artifact sizes are slightly larger

**Revisit when**

- We need a native module Expo can't expose, or
- Build-time customization exceeds what `app.config.ts` permits

## Alternatives considered

- **Bare React Native** — rejected; we'd carry Xcode/Gradle complexity from day 1 for value we don't yet need
- **Flutter** — rejected; we want one language across UI and shared types, and the TS contract is core
