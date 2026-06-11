# ADR-007 — Design Tokens Only; No Inline Colors or Magic Numbers

**Status:** Accepted
**Date:** 2026-06-06
**Phase introduced:** 1

## Context

Premium feel is not a bonus feature — it's the product's identity. The most common failure mode for design-system-led products is the slow drift: someone writes `padding: 13`, someone else picks `#1A1A1A` instead of the card token, and within six months the codebase has 400 close-but-not-quite values. The result reads as cheap.

## Decision

Every color, font size, font weight, line height, spacing value, and radius lives in `packages/design-system/src/tokens/` and is consumed via the `useTheme()` hook. Hex literals at call sites are caught by an ESLint rule (`no-restricted-syntax` matching `#[0-9a-fA-F]{3,8}`). The only exempt folder is `packages/design-system/src/tokens/` itself.

The lint rule is in place from Phase 1 day 1.

## Consequences

**Positive**

- The design system is the single source of visual truth, enforced mechanically
- Theming and future light-mode toggles work without per-component changes
- Every PR with a UI change is reviewable against tokens, not pixels

**Negative**

- Slight friction adding new tokens (must go through `packages/design-system/`)
- One-off exceptions must be discussed, not snuck in

**Revisit when**

- We need conditional styling that tokens can't express cleanly (likely never)

## Alternatives considered

- **Code review enforcement only** — rejected; people get tired, the drift wins
- **Storybook-only enforcement** — rejected; tokens-at-call-sites is the actual problem
