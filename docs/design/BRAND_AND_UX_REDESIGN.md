# ORYX Brand and Product Experience Redesign

**Status:** Discovery and direction  
**Product name:** ORYX (retained; renaming is out of scope)  
**Scope:** Brand identity, visual system, navigation, interaction design, responsive UX and accessibility.

## 1. Product ambition

Make ORYX feel like a calm, clear and dependable financial-intelligence workspace. The product may contain sophisticated research, verification, analysis, publishing, collaboration and operational workflows, but users should not need to understand that internal complexity to complete everyday tasks.

The design must be original. Google and Apple are references for clarity, restraint and consistency, not templates to copy. ORYX needs its own recognisable visual identity.

## 2. Design principles

1. **Clarity before decoration:** every screen makes its purpose, current state and next useful action obvious.
2. **Progressive disclosure:** essentials first; advanced filters and configuration remain discoverable.
3. **Quiet confidence:** restrained colour, typography and motion. Avoid ornamental gradients, excessive borders and dashboard noise.
4. **Consistent behaviour:** shared controls look and behave consistently across web and native mobile.
5. **Readable by default:** legible type, sufficient contrast, clear focus states, comfortable touch targets and meaningful empty/error/loading states.
6. **Data integrity:** never present illustrative counts or fabricated market data as live. Distinguish live, delayed, sample and unavailable data.
7. **Responsive by design:** desktop, tablet and mobile each get intentional layouts.
8. **Accessible interaction:** keyboard navigation, screen-reader labels, focus order, reduced motion and non-colour status cues are first-class requirements.
9. **Respect attention:** badges, animations and alerts must be purposeful.
10. **Preserve working behaviour:** visual refactors retain navigation destinations, permissions, API contracts and tested workflows.

## 3. Brand system

### Logo and symbol

The existing HornMark is a starting point, not a permanent constraint. Evaluate it against:
- Recognition at favicon and app-icon sizes.
- Distinctiveness in monochrome.
- Legibility on light and dark backgrounds.
- Balanced geometry and negative space.
- Clean vector rendering without requiring glow or gradients.
- A natural pairing with the ORYX wordmark.

Explore a few genuinely different logo directions. Keep the ORYX name unchanged. Do not replace the production mark until small-size, monochrome and platform-icon checks pass.

### Colour strategy

The current product has a very dark interface with indigo/violet accents and a separately implemented light theme. Treat this as a baseline, not a final decision.

Explore a restrained, neutral-first system:
- Neutral surfaces and text form the foundation.
- One distinctive ORYX accent is used sparingly for primary actions, selected navigation and focus.
- Green, red, amber and blue are reserved for semantic meaning (positive, negative, warning, information), not general decoration.
- Financial gain/loss states must not rely on colour alone.
- Every text/surface pairing is checked for WCAG contrast.

Do not select a final hue or assume light-first/dark-first until actual app screens have been reviewed in both themes and with realistic data density. Define semantic tokens, not scattered hex values.

### Typography and iconography

Evaluate a compact type scale for page titles, section headings, body copy, labels, metadata and tabular financial values. Use tabular numerals for prices, percentages and aligned figures. Reduce tiny uppercase mono labels where they harm readability.

Use one coherent icon family with consistent stroke weight and optical size. Icons support labels; they should not replace important navigation labels without a strong mobile-specific reason.

## 4. Product UX

### Navigation

Current implementation has a grouped desktop sidebar with numerous destinations, including pending destinations, while native mobile exposes seven bottom tabs. This creates an opportunity to simplify the information architecture.

Before changing routes, map:
- User goals and common tasks.
- Which destinations are first-class workflows versus secondary tools.
- Which features are unavailable and how to represent them honestly.
- Which destinations users need most often on mobile.

Then propose a smaller primary navigation with contextual sub-navigation, useful search/command access and a predictable place for account/workspace controls. Preserve deep links and route behaviour.

### Command Center

The home screen should answer, in order:
1. What is happening?
2. What needs my attention?
3. What can I do next?
4. Where can I continue recent work?

Prioritise useful actions and meaningful summaries over a wall of equal-weight cards. Empty states should teach the first useful action. Do not show empty charts or sample metrics as live.

### Workflow design

Review the full journey through intake/source management, verification/research, analysis/content creation, publishing/follow-up, team/activity/settings. Reduce unnecessary steps, duplicated inputs, jargon and context switching. Provide clear progress, save states, validation and recovery paths. Never hide permissions, irreversible actions or data provenance.

### Responsive and mobile

Audit real device widths and touch interaction. Mobile navigation should prioritise frequent destinations and move secondary destinations into a clearly labelled accessible location. Do not simply shrink the desktop sidebar or force seven equally weighted tabs into the bottom bar.

## 5. Verified starting observations

Based on code inspection:
- A shared design system exists in `packages/design-system`, with semantic colour tokens, typography, spacing, radii, shadows and theme definitions.
- Both dark and light theme objects exist; dark is currently the default.
- The current logo component is `HornMark` in `packages/design-system/src/components/HornMark.tsx`, a gradient-based two-horn SVG.
- Desktop navigation is centrally defined in `apps/mobile/src/components/web/webNav.ts` and includes multiple groups and pending destinations.
- `WebShell` provides a desktop sidebar/top bar and collapses the sidebar into a drawer at narrower widths.
- Native navigation is defined in `apps/mobile/src/navigation/RootTabNavigator.tsx` and currently has seven tabs.
- `docs/design-reference/` is a visual prototype. The production application lives in `apps/mobile/`; changes must target the production UI and preserve real data and navigation behaviour.

These are code-level observations, not a claim that every screen has been visually inspected or usability-tested. A screen-by-screen review and local runtime inspection remain necessary.

## 6. Delivery plan

### Phase 0 — Discovery and baseline
- Capture key production screens at desktop and mobile widths in both themes.
- Map routes, feature maturity, user journeys and component usage.
- Identify UX friction, visual inconsistency, accessibility issues and unfinished states.
- Record baseline screenshots and relevant tests.

### Phase 1 — Brand exploration
- Develop original logo and wordmark directions.
- Explore neutral-first colour directions and typography.
- Test contrast, monochrome, small-size rendering and light/dark use.
- Select and document a direction before implementation.

### Phase 2 — Design-system foundation
- Refine semantic tokens and component primitives.
- Establish type, spacing, surface, border, elevation, focus and motion rules.
- Standardise buttons, inputs, cards, navigation, tables, badges, dialogs and empty/loading/error states.
- Add token/component tests and accessibility checks.

### Phase 3 — Core application experience
- Simplify navigation and responsive app shell.
- Redesign Command Center around attention and next actions.
- Improve high-frequency end-to-end workflows.
- Keep feature redesigns in small, reviewable PRs.

### Phase 4 — System-wide consistency
- Apply the system to remaining screens.
- Refine mobile layouts, accessibility, responsive behaviour and micro-interactions.
- Remove obsolete styles only after consumers migrate.

### Phase 5 — Validation
- Run lint, type checks, unit/integration tests and relevant end-to-end checks.
- Verify navigation, authentication, workspace switching, permissions and deep links.
- Compare before/after screenshots at supported viewport sizes.
- Validate both themes and keyboard/screen-reader interactions.
- A green CI run alone does not establish production readiness.

## 7. Implementation guardrails

- Work in small, focused PRs; no giant all-at-once redesign.
- Preserve API contracts, backend behaviour, permissions and data semantics.
- Do not add a new UI framework or duplicate design system without demonstrated need.
- Avoid hard-coded colours and one-off styles.
- Do not make unfinished features appear operational.
- Do not remove functionality without a product decision.
- Keep tests meaningful; add regression coverage for navigation and shared components.
- Include before/after visual evidence for material changes when available.
- The user reviews and merges PRs unless they explicitly delegate merging.

## 8. Definition of done

- Users can identify the purpose and next action on each major screen quickly.
- Common tasks require fewer confusing decisions and less context switching.
- The identity is recognisable without depending on gradients or decoration.
- Light and dark themes are coherent and accessible.
- Desktop and mobile feel purpose-built.
- Components expose accessible labels and focus states.
- Real data, loading, empty, error and permission states are handled honestly.
- Existing workflows and security boundaries pass regression tests.
- Future screens can follow the documented system consistently.

## 9. Immediate next actions

1. Capture and inspect key production screens at desktop and mobile widths.
2. Map navigation and distinguish primary versus secondary destinations using actual feature maturity.
3. Produce original logo/wordmark explorations and two or three neutral-first colour directions.
4. Present the recommended brand direction and rationale before changing production tokens.
