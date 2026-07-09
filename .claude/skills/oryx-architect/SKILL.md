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

**Color tokens — "Genspark cool-dark" (CURRENT; do not introduce new ones without explicit reason):**
```
Brand mark (logo horns, SVG):  gradient #08314A → #03121D (2026-07-05 teal
                                 retirement; was teal #14B8A6 → #0E8C82). The
                                 Genspark SVG horn mark remains the CANONICAL
                                 logo. Inner-curl stroke = bg #05070A.
UI accent family:               indigo #5B5BF5 (PRIMARY — CTAs, active states; the
                                 primary "fill" is the indigo→violet gradient
                                 135°), violet #8B5CF6 (secondary/solo accent),
                                 "teal" keys now hold #08314A + #041F35 (SURFACE-
                                 ONLY: 1.49:1 vs bg — marks/text use
                                 semantic.positiveText #30A3E9), softblue #60A5FA.
Base/backgrounds (cool dark):   bg #05070A, panel #0A0E14, elev #10151D,
                                 elev-2 #161D28; border #1A2330, border-strong
                                 #232F42, hairline rgba(255,255,255,0.04).
Text (cool grey ramp):          text #E6EAF2, text-2 #A8B0BF, text-3 #6B7588,
                                 text-4 #4A5263.
Text-on-fill:                   #fff on the accent gradient (.btn.primary). This
                                 system uses white-on-accent, NOT same-family dark.
Semantic:                       positive SPLIT 2026-07-05 (old single pos/success
                                 retired): positiveSurface #08314A (fills only) +
                                 positiveText #30A3E9 (computed WCAG 7.24:1 vs bg,
                                 6.95:1 vs panel). neg #F87171, warn #F59E0B,
                                 info #60A5FA unchanged.
SUPERSEDED 2026-06-29 (owner-confirmed GLOBAL reversal): "Midnight Citrus"
  (warm base + amber-primary, commit 404e066, 2026-06-28) is RETIRED. The
  canonical system is now an EXACT 1:1 port of the approved Genspark source
  (docs/design-reference/*). Tokens live in packages/design-system/src/tokens
  (gensparkPalette = the literal :root mirror; the structured `colors` keys were
  value-remapped onto Genspark hexes so 100+ call sites kept compiling — e.g.
  accent.amber now HOLDS indigo #5B5BF5, text.onAmber now HOLDS #fff). When you
  see `amber`/`coral`/`onAmber` key NAMES in code, they carry Genspark values,
  not warm hues — read tokens/colors.ts before assuming a hue from a key name.
  Gradients are start/end pair tokens (`gradients.*`) consumed via
  expo-linear-gradient (RN has no CSS gradient string). The historical
  "Midnight Citrus" and the even-earlier teal-primary sets are both dead.
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

- FRONTEND TESTS: PURE-LOGIC ONLY (updated Phase 6 Wave B, 2026-07-07). The
  mobile `test` script now runs node's built-in test runner via tsx
  (`tsx --test <explicit .test.ts files>`) — tsx is a mobile devDep linked from
  the pnpm store. This works ONLY for pure TypeScript modules with no
  react-native imports (e.g. label maps, presenters like
  modules/automation/feed.ts); the convention is to extract screen logic into
  such modules and test those. There is STILL no component/render test runner —
  jest-expo + babel + RN mocks were never stood up; that remains its own infra
  task, and a report claiming component tests pass should still be rejected.
  ADDENDUM (Phase 7 Wave B, 2026-07-08): the `test` script is an EXPLICIT file
  list — a new `.test.ts` file that isn't appended to it silently never runs;
  adding the file to the list is part of adding the test.

- CHARTS ARE HAND-ROLLED react-native-svg, NO CHARTING LIBRARY (confirmed
  Phase 7 Wave B). The design system's Spark (sparkline) and Candles
  (candlestick) are the precedent: react-native-svg primitives + theme tokens
  (grid = border.default, axis text = text.tertiary in JetBrains Mono, data
  marks must use tones that READ against the dark ramp — semantic.positiveText
  or accent.slateBlue, never accent.teal). New chart types follow this shape
  (see modules/analytics/components/BarSeries.tsx); do not add a charting
  dependency without an explicit decision.
  New pure test files must be added to the mobile package.json test script's
  explicit file list (no glob — Windows scripts don't expand them). The other
  frontend gates are unchanged: `pnpm type-check`, `pnpm lint` (warnings-only
  passing; ~36 pre-existing sort-imports warnings), `pnpm drift:check`.
- ENUM-WIDENING DRIFT IS SILENT (Phase 6 Wave B found this the hard way). A
  migration that widens a Postgres enum (0014 added 'verification'/'publishing'
  to activity_type) does NOT force the shared-types mirror to follow:
  `pnpm drift:check` only verifies types.py PARSES, not that its Literals match
  the TS or the DB. Wave A shipped with ActivityType missing both new values on
  BOTH sides, so GET /activity/inbox crashed (pydantic literal_error) on any
  dispatched row — a latent 500 no test caught until Wave B's UI work hit it.
  When a migration touches an enum, grep BOTH packages/shared-types/src and
  oryx/shared/types.py for that enum's Literal and widen them in the same
  commit; regression test: test_activity_inbox_serializes_phase6_categories.
  ADDENDUM (email-delivery wave, 2026-07-10): AutomationAction has a THIRD
  mirror — apps/mobile/src/modules/automation/feed.ts's ACTION_COPY is an
  exhaustive Record<AutomationAction, ...>, so widening the union without
  adding copy entries there fails `pnpm type-check` (a feature: the compiler
  enforces what drift:check can't). Widen all three in the same commit.
- react-native-svg IS NOT a direct mobile dependency, but it's a (currently
  UNMET) peerDependency of lucide-react-native, which the shipped Icon component
  uses. The exact-for-RN-0.74 version (15.15.5) already sits in the pnpm store,
  so anything needing real SVG paths (e.g. the HornMark brand motif) should
  declare `react-native-svg` on apps/mobile and `pnpm install --offline` (links
  from store, downloads nothing) rather than approximating with bordered Views.
- Typography is no longer the strict six-size set (Genspark port, 2026-06-29).
  The variant set now mirrors the Genspark type scale (pageTitle/kpiVal/wordmark/
  cardTitle/navLabel/navGroup/body/bodySm/caption/label/mono, + retained display/
  h1/h2). Text STILL rejects raw fontSize/fontWeight at call sites — pick a
  variant, don't invent a size. FONTS ARE NOW REALLY LOADED: Inter (400/500/600/
  700) + JetBrains Mono (400/500/600) via @expo-google-fonts, gated in App.tsx
  (useAppFonts) — the prior "fonts referenced but not loaded" state is fixed; the
  ttf files are bundled by metro (no runtime network fetch). Shared, cross-module
  components live in `apps/mobile/src/components/` (ErrorBoundary, FeatureGate,
  EmptyState, HornMark[now re-exports the design-system mark], plus web/ for the
  WebShell/WebSidebar/WebTopBar); there is no `src/_shared/components/`.
- SVG PRIMITIVES + GENSPARK ICONS now live in the design-system package
  (HornMark, Spark, Candles, GensparkIcon) and need react-native-svg, which is
  now a declared peer+dev dep of @oryx/design-system (15.15.5, from the pnpm
  store). The canonical HornMark is the Genspark gradient SVG (200×200 viewBox,
  teal #14B8A6→#0E8C82), not the old 2-path line-art. The lucide-based `Icon`
  is retained for native screens; GensparkIcon is additive (web sidebar/topbar).
- WEB GETS A DESKTOP SHELL, NATIVE KEEPS BOTTOM TABS. App.tsx now wraps the
  navigator in WebShell (replaced WebFrame). WebShell is pass-through on native
  and renders the ported 232px sidebar + 44px topbar on web (Platform.OS==='web'),
  driving the real tab navigator via a navigationRef. RootTabNavigator hides its
  bottom tab bar on web (`tabBarStyle: { display: 'none' }`). The sidebar shows
  REAL /me data (workspace, profile, build version); the ticker strip is empty
  ("live data pending") and pending nav items are dimmed — no fake demo data.

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
- PRIMARY BUTTON LABEL IS NOW WHITE-ON-ACCENT (Genspark port, 2026-06-29). The
  design-system Button primary still passes `color="onAmber"`, but that token now
  HOLDS #fff (Genspark .btn.primary uses white text on the indigo→violet accent).
  The fill is currently the SOLID indigo #5B5BF5 (accent.amber remapped), NOT the
  full indigo→violet gradient — Button.tsx was not refactored to render a
  LinearGradient. A faithful gradient primary is a documented follow-up (gx.btnPrimary
  + gradients.accent exist for it). History: Midnight Citrus had dark-on-amber
  #2B1A04; before that, inverse on teal. Read Button.tsx + tokens/colors.ts first.
- BRAND-vs-SEMANTIC AMBER COLLISION — RESOLVED by the Genspark port (2026-06-29).
  The brand primary is no longer amber (now indigo #5B5BF5), so it no longer
  collides with the semantic ambers. semantic.warning is now #F59E0B (Genspark
  --warn) and the local severity/draft/status `#F59E0B` consts are unchanged —
  they're now hue-distinct from the indigo/violet brand. Still do NOT recolor a
  semantic token on your own judgment; that remains an owner decision.
- RESERVED LogRecord ATTRIBUTES CRASH `extra={...}` — AND ONLY AT INFO (Phase 6
  Wave A bug). stdlib logging's makeRecord raises KeyError for any `extra` key
  that shadows a built-in LogRecord attribute (`created`, `name`, `msg`,
  `levelname`, `module`, `process`, ...). Two traps: (1) the crash happens AFTER
  the DB commit in a bus handler, so the drainer records a spurious failure and
  the idempotent retry then "succeeds" — the bug self-masks in production while
  polluting retry metrics; (2) it only fires when the logger is enabled for that
  level, so a `logger.info` call with a bad key passes every test until
  something turns INFO on. Which is exactly what test_logging_redaction.py did:
  it called configure_logging() (root → INFO, handlers replaced) and never
  restored state, making dispatcher tests fail only in full-suite order (fixed
  with try/finally restore, commit 5b16133). When adding structured log calls,
  check keys against LogRecord attrs; when a test calls configure_logging(),
  snapshot and restore root level + handlers.

- MOBILE PUSH: RAW TOKENS NEED A DEV BUILD — THE CODE GUARDS ITSELF (Phase 6
  Wave C). ORYX's FCMProvider/APNsProvider send directly to Firebase/Apple, so
  the client must register expo-notifications' getDevicePushTokenAsync() RAW
  token, never getExpoPushTokenAsync()'s ExpoPushToken[...] relay format. Raw
  tokens carry the app's own push identity, which exists only in a
  development/production build with native push config (Android:
  app.json android.googleServicesFile + a Firebase project; iOS: aps-environment
  entitlement from a provisioned build). The project is Expo Go-configured (no
  expo-dev-client), so lib/push/registration.ts HARD-SKIPS Expo Go
  (Constants.executionEnvironment === 'storeClient') and web — an unusable
  token can never reach alert_devices; registration self-activates on the
  first dev build. Related toolchain quirks: `npx expo install` cannot spawn
  pnpm under this shell (cross-spawn ENOENT) — read the right version from
  node_modules/expo/bundledNativeModules.json and `pnpm --filter @oryx/mobile
  add pkg@version` instead; expo-notifications 0.28 does NOT re-export the
  PermissionStatus enum — compare the status strings
  ('granted'/'denied'/'undetermined') directly.
- automation_log IS KEYED PER CHANNEL SINCE WAVE C (migration 0017). The
  idempotency key is UNIQUE(account_id, triggered_by_event_id, channel) — one
  decision row per (account, event) per delivery channel ('in_app' | 'push',
  'email' reserved). The channel column has NO default anywhere (server_default
  was dropped on purpose): every insert must state its channel explicitly, and
  any new automation_log writer that omits it fails loudly. Dispatcher tests
  that count log rows must scope to a channel — every dispatch now also writes
  a push-slot row (push_failed when no device is registered, per the frozen
  "no silent skip" rule), so unscoped `len(logs) == 1` asserts are wrong.
- THE EVENT CATALOG IS BIGGER THAN THE CONSTANTS FILES (Phase 7 Wave A found
  this after the Phase 7 doc froze on "20 events"). Two lifecycle events are
  published as STRING LITERALS, not constants: workspace.deletion.started /
  workspace.deletion.completed (intake/workspace_cascade.py), BOTH with
  workspace_id=None (the workspace row is mid-deletion; its id rides in the
  payload). Any "list every event" sweep must grep enqueue_event( call sites
  for name=, not just services/*/events/constants.py — and note intake's
  constant lives at the nonstandard services/intake/events_constants.py. The
  AnalyticsAggregator deliberately does NOT subscribe to the two deletion
  events (no workspace to attribute, no metric) and skips-with-warning any
  event that arrives without a workspace_id. Related shape facts:
  DomainEvent.id IS the outbox row id (queue/outbox.py mints one uuid for
  both) — that's the analytics dedup key; digest_runs is ACCOUNT-scoped, so
  workspace-keyed aggregation joins through workspace_members.

## What This Skill Deliberately Does NOT Contain

Current phase/wave status, current commit hashes, current test counts.
These change too fast to hardcode safely. Check memory, ask the user, or
read the actual repo/report in front of you. Treat any phase-status claim
in this file as instantly stale if found — there shouldn't be one.
