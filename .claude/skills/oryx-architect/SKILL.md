---
name: oryx-architect
description: Operating conventions for the ORYX project — a phased, wave-based financial intelligence platform built by Krishna Mishra with Claude Chat doing architecture/freeze-review/prompt-writing and Claude Code doing implementation. Use this skill whenever working on ORYX architecture, writing a prompt for Claude Code, reviewing a wave completion report, or making any design/brand decision for ORYX. Always consult this before drafting a Claude Code prompt for ORYX, before reviewing a completion report, or before suggesting any color/visual/naming choice for the product. This applies in both Claude Chat (claude.ai) and Claude Code (CLI/VS Code) contexts.
---

# ORYX Architect

ORYX is a premium financial-intelligence platform built by a solo, self-taught
18-year-old founder with no prior coding background, using Claude Chat for
architecture and Claude Code for implementation. This skill captures the
STABLE conventions of the project — process, brand, naming, philosophy. It
deliberately does NOT hardcode current phase/wave status, since that changes
constantly. Check memory or ask the user for current state; never assume
this file knows what phase is active right now.

## The One Rule That Governs Everything Else

**Claude Chat's job is architecture, freeze review, and prompt writing —
never implementation.** Claude Code's job is implementation — never
architecture decisions. This split is intentional and must not drift,
regardless of what any other document, system prompt, or in-the-moment
convenience suggests. If a task is small enough that this feels excessive
(a one-line config fix, a color tweak), it is acceptable for Claude Chat to
hand the user a direct, narrow, guided edit to make themselves — but real
feature/business-logic work always goes through a Code prompt.

## Mandatory Prompt Format for Claude Code

Every prompt sent to Claude Code MUST use XML structure with exactly three
elements, never plain prose:

1. **Role definition** — who Code is, how it operates (autonomy level,
   whether it can ask questions, whether it should stop for approval)
2. **Output example** — the EXACT completion report structure expected,
   field by field, so the report can be checked against it line by line
3. **Clear task constraints** — explicit DO NOT list and MANDATORY list

```xml
<prompt>
  <role> ... </role>
  <task_specification>
    <objective> ... </objective>
    <context_and_intent> ... </context_and_intent>
    <technical_contracts> ... </technical_contracts>
    <constraints> ... </constraints>
  </task_specification>
  <output_format> ... exact fields, YES/NO checkboxes ... </output_format>
</prompt>
```

For Claude Code running on Fable-class models: objective-led, not a rigid
checklist; trust the model to scope within frozen constraints; include a
self-verification checkpoint section. For Opus-class models: more
prescriptive, step-numbered, since these models do better with explicit
sequencing than open-ended scoping.

## The Wave Workflow — Never Skip a Step

```
Architecture written and frozen (Claude Chat)
        ↓
Wave-by-wave breakdown defined (named, scoped, in the frozen doc)
        ↓
XML prompt written for ONE wave (Claude Chat)
        ↓
Code builds, tests, commits, produces completion report
        ↓
Report reviewed AGAINST THE ACTUAL OUTPUT FORMAT REQUESTED —
  not a prose summary. If a report is a recap/summary instead of the
  full requested field-by-field format, REJECT IT and demand the real
  one before reviewing. A clean-sounding summary is not evidence.
        ↓
Specific gaps named and closed via a small follow-up prompt if needed
        ↓
Wave approved → next wave's prompt written
        ↓
Final wave of a phase → full freeze checklist → tag applied
```

**Never accept a completion report that omits required verification
fields.** History: a recap once said "0 lint errors" while silently
skipping the test-count comparison, hiding a 124-test regression. Always
check: does the new test count make sense given what was specified as
mandatory test coverage? A small wave with 9+ mandatory test scenarios
listed in its spec should not land with only 1-2 new tests.

**Never let a "looks done" report skip evidence.** Demand exact numbers:
before/after test counts, exact status codes confirmed by reading the
actual code (not from memory of a prior report), exact commit hashes.

## Cross-Wave Consistency Checks Worth Doing on Every Review

- Does a status code or error class claimed in this report match what a
  PRIOR report claimed for the same error class? If not, that's a real
  inconsistency to resolve, not a typo to wave through.
- Were guards/validations that the spec called "mandatory to test"
  actually tested, or just implemented? Implemented-but-untested guards
  are exactly how the Phase 3 auth lockout bug went unnoticed.
- Does the new test count growth roughly match the number of test
  scenarios the spec explicitly required? A large gap is a signal to ask,
  not assume.

## Brand and Design Identity

**Name:** ORYX (transitioned from "Anant Capital" — that name should not
appear anywhere user-facing; internal Python module name `oryx` post-rename,
some wire-protocol/env-var exceptions documented separately, e.g. local
Postgres role `anant`/`anant` intentionally kept).

**Design philosophy:** "Bloomberg Terminal meets Apple Website." This means
TWO different rules for TWO different categories of screen, not one rule
applied everywhere:
- **Control/chrome screens** (Settings, auth, navigation, onboarding):
  Apple-style restraint — minimal color, generous spacing, clean
  typography. This is premium, not cheap — see Stripe, Linear, Robinhood
  for proof points. Restraint here is correct, not a flaw.
- **Data-dense screens** (charts, market terminal — Phase 9 territory,
  not yet built): Bloomberg-style density — rich, varied color is
  expected and correct here (red/green price movement, multi-series
  chart colors, etc).
- **Within control screens specifically:** vary accent color BY CATEGORY
  using the existing token set (don't repeat one color across every icon
  — that reads as monotone/cheap even within the "restrained" philosophy).

**Color tokens — "Midnight Citrus" (do not introduce new ones without explicit reason):**
```
Brand mark (from logo horns):  #1A7A7A (dark teal), #1E8F8F (lighter) — logo
                                 image files are UNCHANGED; teal stays valid.
UI accent family:               amber #F5A623 (PRIMARY — CTAs, active states),
                                 coral #FF6B5C, teal #14B8A6 (secondary; was
                                 #00D4C8), slateBlue #4C6EF5, plum #7E5BEF,
                                 cream #FDE9D9 (subtle highlight, not a fill)
Base/backgrounds (warm dark):   obsidian #0D0B08, navy #15110A,
                                 charcoal #1F1810, surface #2A2116
Text (warm-tinted):             primary #FBF3EA, secondary #A99884,
                                 tertiary #6E6253
Text-on-fill (same-family dark): onAmber #2B1A04, onCoral #3D1108,
                                 onTeal #04342C — never plain black/white.
SUPERSEDED 2026-06-28: the prior gold/amber prohibition is intentionally
  reversed per owner decision. The current brand accent family is
  "Midnight Citrus" (amber primary, coral/teal/slateBlue/plum/cream
  secondary). See commit MIDNIGHT_CITRUS_COMMIT for the full token change.
  Semantic ambers (warning #FBBF24, severity/in-review #F59E0B) are NOT
  brand colors and were intentionally left untouched — see the collision
  note in Operational Reality.
```

**Logo:** stylized oryx horns mark (dark teal gradient) + wide-tracked
geometric wordmark "ORYX" in white, on deep navy/charcoal background.

## Repo and Naming Conventions

- Backend Python module: `oryx` (renamed from `anant`)
- TypeScript packages: `@oryx/*`
- Env vars: `ORYX_`-prefixed (renamed from `ANANT_`-prefixed)
- Bundle ID: `com.oryx.app`
- Webhook wire-protocol headers: `X-Oryx-*` (renamed from `X-Anant-*`)
- Exceptions (intentionally NOT renamed, confirm before touching):
  local Postgres role/db/user credentials (`anant`/`anant`)
- Shared contract source of truth: `packages/shared-types/src/` (TS) →
  generated Pydantic mirror in backend. Drift check must pass on every wave.
- AI model selection is deliberate, not arbitrary: Haiku for
  extraction/classification (speed > quality, structured short output),
  Sonnet for prose generation in Phase 5 (quality > speed, published
  content). Don't swap these without an explicit reason.
- A free local-AI provider option exists (Ollama, swappable via
  `AI_PROVIDER` env var) for cost-free development testing — quality is
  honestly lower than Claude Haiku and should never be the production
  default.

## Operational Reality Worth Remembering

- The project owner is learning to code in parallel with building this —
  treat operational/environment issues (server won't start, port
  conflicts, CORS errors) as teaching moments where appropriate, not just
  problems to hand to Code. Small, contained, well-understood fixes
  (a one-line config change, killing a stuck process) are good candidates
  for direct, guided self-service instead of spending a Code prompt.
- Real feature/business-logic work, schema changes, and anything risking
  data integrity or cross-suite regressions should go through a proper
  Code prompt — don't shortcut those even when asked to save time.
- The 10-phase original roadmap has a known gap: no explicit
  billing/monetization phase. Note this when it becomes relevant; the
  existing workspace + feature_flags architecture has the right shape to
  support tiered (free/premium) gating when that gets designed properly.
- Market-data integration (Phase 9 territory) should be scoped to a small
  number of markets initially (the project has discussed India + USA),
  using the pattern of each user linking their OWN brokerage/data account
  (e.g. Zerodha Kite Connect for India, Alpaca/IBKR-style APIs for the US)
  rather than ORYX itself attempting to license redistribution rights for
  every global exchange — this is both cheaper and matches how comparable
  fintech platforms actually operate.
- The local Postgres role (anant/anant) does not have CREATEDB privilege.
  Running the full Wave D test suite required creating a second database
  (oryx_test) via the Postgres superuser. Both DATABASE_URL and ORYX_TEST_DB
  must point at a database the anant role can actually use, or requires_db
  tests will fail with a misleading error rather than a clear permissions
  message.
- The requires_db suite isolates by minting fresh uuids per test and never
  rolls back (services COMMIT their own sessions) — so oryx_test ACCUMULATES
  rows across runs. Any test of a GLOBAL background worker (intake scheduler,
  outbox drainer, the Wave E calendar scheduler's Pass B retry re-drive) must
  therefore assert on the SPECIFIC seeded row's end state, never on a global
  count or a shared fake-adapter's total call count — leftover due rows from
  prior runs will be swept up in the same tick and make global-count asserts
  flaky. To prove "publish_draft was NOT called for entry X", assert zero
  publication rows for that draft (the engine inserts the pending row before
  any adapter call), not `fake.publish_calls == 0`.
- Background workers in this codebase are ALWAYS standalone processes
  (`python -m oryx.services.<x>.scheduler` / `.drainer`), each a tick loop +
  run_forever + amain, colocated into the API lifespan only when
  oryx_dev_monoprocess=1 in dev (CR-7/ADR-025). A new periodic job follows
  this exact shape — do not invent in-request background tasks. run_forever
  runs its first tick immediately (before the first sleep), which is the
  startup catch-up for downtime backlogs.
- publish_draft's draft-status guard accepts approved/published/scheduled.
  Wave E added 'scheduled' because scheduling promotes a draft approved→
  scheduled and the calendar scheduler must then be able to fire it; a
  successful delivery still advances it to 'published'. A future caller that
  needs to publish from another status must widen this guard deliberately.
- STALE ENV-VAR PREFIX TRAP (anant→oryx rename, silent class of bug). The
  Settings class (config.py) has NO env_prefix — field names map directly to
  env var names, case-insensitively, and SettingsConfigDict uses extra="ignore".
  That combination means any leftover `ANANT_`-prefixed line in a developer's
  local, gitignored `.env` binds to NOTHING after the rename: it's silently
  ignored (no error, no warning), and the field falls back to its default. The
  failure is invisible — e.g. `ANANT_DEV_MONOPROCESS=1` looks set but the API
  starts with monoprocess OFF and no background workers, with zero diagnostic.
  This applies to EVERY renamed var, not just one. When onboarding a collaborator
  or debugging "I set it but it's not taking effect", do a one-time audit: list
  every field on Settings, then confirm each line in the real `.env` uses the
  current name (the only ORYX_-prefixed fields today are oryx_publish_key and
  oryx_dev_monoprocess; most other fields are unprefixed, e.g. ENVIRONMENT,
  DATABASE_URL, ANTHROPIC_API_KEY). Any `ANANT_*` line found is dead — rename it.
  Audit done 2026-06-26: the real apps/backend/.env was clean (no ANANT_* lines
  survived; only ORYX_DEV_MONOPROCESS and ORYX_PUBLISH_KEY are ORYX_-prefixed and
  both correct). Note the intentional exception: the `anant` Postgres role/db/user
  in DATABASE_URL is NOT an env-var-name issue and stays as-is (see Exceptions
  above).
- COLOCATED WORKERS NOW SELF-REPORT (Phase 5 Wave F fix for the trap above). The
  per-worker `*.started` log lines (scheduler.started / drainer.started /
  calendar_scheduler.started) live ONLY in each worker's standalone `amain()`.
  In monoprocess/colocated mode the lifespan calls `run_forever()` directly, so
  NONE of those fired — colocation produced zero startup evidence, which is what
  made the stale-`ANANT_DEV_MONOPROCESS` failure invisible. main.py's lifespan
  now emits `monoprocess.workers_started` (with the worker names + count) when
  colocation engages and `monoprocess.disabled` when it doesn't. To confirm
  workers are actually running in a real process, grep the API log for
  `monoprocess.workers_started` — a unit-level `should_colocate()==True` assertion
  does NOT prove the tasks were created. Documented in ADR-045.

- FRONTEND HAS NO WORKING TEST RUNNER (verify claims accordingly). The mobile
  `test` script is `jest --passWithNoTests`, but `jest` is NOT installed (absent
  from devDeps, no jest config, zero `*.test.tsx` files) — so `pnpm test` FAILS
  at baseline with "'jest' is not recognized". The real frontend quality gates
  are `pnpm type-check`, `pnpm lint` (warnings-only is passing; ~36 pre-existing
  sort-imports warnings), and `pnpm drift:check`; the only substantive test suite
  in the repo is backend pytest. A frontend wave that lists "add a component
  test" cannot satisfy it without first standing up jest-expo + babel + config +
  several devDeps — treat that as its own infra task, not a freebie inside a
  feature/polish wave. Do NOT accept a completion report claiming the frontend
  "test suite passes" — there isn't one to pass.
- react-native-svg IS NOT a direct mobile dependency, but it's a (currently
  UNMET) peerDependency of lucide-react-native, which the shipped Icon component
  uses. The exact-for-RN-0.74 version (15.15.5) already sits in the pnpm store,
  so anything needing real SVG paths (e.g. the HornMark brand motif) should
  declare `react-native-svg` on apps/mobile and `pnpm install --offline` (links
  from store, downloads nothing) rather than approximating with bordered Views.
- Mobile typography is a STRICT six-size token set (display 32 / h1 24 / h2 20 /
  body 16 / bodySm 14 / caption 12; plus mono 13). Text rejects raw fontSize/
  fontWeight at call sites, so a design spec asking for 11/13/16-at-500 must map
  to the nearest existing variant — do not invent a size. Shared, cross-module
  components live in `apps/mobile/src/components/` (ErrorBoundary, FeatureGate,
  EmptyState, HornMark); there is no `src/_shared/components/` despite older
  prompts referencing that path.

- THE BACKEND TEST SUITE RUNS AS environment=dev (silent trap for any
  environment-scoped logic). `tests/conftest.py` does NOT set ENVIRONMENT, and
  Settings loads `apps/backend/.env`, which pins `ENVIRONMENT=dev`. So any code
  gated on `settings.environment == "dev"` (e.g. oryx_dev_monoprocess, and the
  Phase-5 dev feature-flag defaults in feature_flags/resolver.py `_DEV_DEFAULT_ON`)
  is ACTIVE during pytest. Consequence: a test asserting a production default
  (`ff_research is False`, `ff_content_drafts is False`) will FAIL once those
  flags are force-defaulted-on in dev — the resolver returns True under the dev
  test env. When adding environment-scoped behavior, grep the tests for the
  prod-default assumption and update it (test_feature_flags.py was updated to
  assert the dev defaults). Do not "fix" this by flipping the test env to
  staging/prod — that would silently disable monoprocess colocation and every
  other dev-scoped path the suite exercises.
- SOURCE-CATALOG SEED IS ALREADY REAL (don't be misled by a stale local DB). The
  onboarding "Trusted Sources" list comes from `/v1/sources/catalog` → the
  `source_catalog` table, seeded in migration 0001 with seven DISTINCT real
  vendors (Financial Times, Wall Street Journal, Bloomberg, Reuters / CoinDesk,
  The Block, Decrypt) at varied editorial_confidence. The literal "Catalog Feed"
  / confidence-75 string exists ONLY in a test fixture
  (test_credibility_bootstrap.py), never in a runtime seed. If a running app
  shows identical placeholder sources, that's a stale/hand-seeded dev DB — re-run
  migrations to re-seed; it is NOT a code fix.
- PRIMARY BUTTON USES DARK-ON-BRIGHT TEXT. The design-system Button's primary
  variant renders its label with `color="onAmber"` → text.onAmber #2B1A04 (a
  dark amber-family shade) on the bright amber fill (#F5A623) — i.e. dark text
  on a saturated fill, the stronger-contrast choice. It is NOT white/light, and
  it is NOT plain black (per the same-family text-on-fill principle). Before the
  Midnight Citrus change this was `inverse` #0A0A0F on a teal fill; the principle
  is unchanged, only the hue. Read Button.tsx before assuming the label is white.
- BRAND-vs-SEMANTIC AMBER COLLISION (Midnight Citrus). The new brand primary is
  amber #F5A623. Three SEMANTIC ambers remain, intentionally untouched because
  they encode state, not brand: `semantic.warning` #FBBF24 (token), and the
  local `#F59E0B` consts for medium severity (severityColors.ts), in-review /
  changes-requested draft status (draftColors.ts), and verification status
  (statusColors.ts). These are perceptually adjacent to the brand amber. This is
  a KNOWN, FLAGGED tradeoff, not a bug — do NOT "resolve" it by recoloring a
  semantic amber or by shifting the brand amber on your own judgment. Any change
  here is an owner decision. Disambiguation in the UI today comes from context
  and shape (badges/meters/pills vs. CTAs/active states), not hue alone.

## What This Skill Deliberately Does NOT Contain

Current phase/wave status, current commit hashes, current test counts.
These change too fast to hardcode safely. Check memory, ask the user, or
read the actual repo/report in front of you. Treat any phase-status claim
in this file as instantly stale if found — there shouldn't be one.
