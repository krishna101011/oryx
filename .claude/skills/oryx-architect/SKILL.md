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
  ADDENDUM (2026-07-14): rendered-component tests ARE now possible without
  jest — apps/mobile/src/test/shims/ aliases ONLY the platform packages
  (react-native, react-native-svg, expo-blur, lucide-react-native,
  react-native-safe-area-context) to inert prop-forwarding hosts via a
  Module._resolveFilename patch (register.js), letting react-test-renderer
  mount real screens + design-system components under `tsx --test`. First
  user: modules/research/rowNavigation.test.tsx (renders the real
  ResearchWorkspaceListScreen, presses a row, asserts
  navigate('ResearchWorkspaceDetail', {rwsId})). TWO TRAPS: (1) load
  register.js via createRequire BEFORE anything importing react-native, and
  load ALL runtime modules in the test through that same require — a dynamic
  import() pulls the ESM build of react-query/react-navigation while product
  code under tsx uses the CJS build, giving two context instances and a
  provider the hook can't see ("No QueryClient set" with a provider plainly
  present). (2) Inject navigation with NavigationContext.Provider (from
  @react-navigation/native) + a recording fake and seed react-query with
  setQueryData + staleTime Infinity — no NavigationContainer, no network.
  ADDENDUM (2026-07-16, second user: modules/automation/expandOnPress.test.tsx):
  screens behind FeatureGate/useMe also need react-redux — wrap in Provider
  with the REAL singleton store (req('../../store').store; default auth status
  'unknown' is fine) and seed ['me'] with { workspace:{id}, flags:{ff_*: true} }.
  useMe's `enabled: status==='authenticated'` only gates FETCHING — useQuery
  still returns seeded cache data when disabled, so FeatureGate opens without
  faking auth. Locate pressables via their accessibility contract and assert
  on JSON.stringify(tree.toJSON()) for rendered/absent copy.
- SSRF GUARD LIVES AT oryx/core/security/ssrf.py (moved 2026-07-24, was
  api_pull-scoped only). `assert_url_safe(url, *, hostname_allowlist=None)`
  raises `UnsafeUrlError(ValueError)` — deliberately NOT tied to any one
  caller's error taxonomy, since it now guards three call sites with three
  different exception types: api_pull (`api_pull/safety.py` is a thin
  adapter translating to `ProviderError(PERMANENT)` — kept for backward
  compat with existing tests/imports), RSS (`rss/client.py` translates
  inline to `ProviderError`), and publishing webhooks
  (`webhook.py` translates to `PermanentChannelError`). ANY new code that
  fetches a workspace-controlled URL must call this guard — do not write a
  parallel check. Two traps found closing the RSS/webhook gap: (1) a
  redirect-following fetcher (RSS does; webhook does not) must re-call the
  guard on EVERY redirect hop, not just the entry URL — an entry URL that
  resolves public proves nothing about where its 302 sends you next; the
  cleanest way is a single guard call at the top of the function if redirect
  handling recurses back into that same function. (2) the guard's DNS check
  makes it IMPOSSIBLE for a hostname that actually resolves to 127.0.0.1 to
  ever pass — so any test that hits a real local `http.server` as a stand-in
  "external" webhook target (a pattern used in several real-e2e tests: HMAC
  signing proof, citations payload shape, the Phase 5 flagship pipeline
  test) now needs `patch("oryx.services.publishing.channels.webhook._assert_url_safe", lambda url: None)`
  around just that publish call — the guard itself is proven for real
  elsewhere (test_ssrf_redirect_and_loopback.py), so bypassing it in tests
  that were never testing SSRF in the first place is correct, not a gap.

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
- ALEMBIC BATCHES ALL PENDING MIGRATIONS INTO ONE TRANSACTION (billing
  foundation wave, 2026-07-25, migration 0029 found this the hard way).
  alembic/env.py's do_run_migrations() wraps context.run_migrations() in a
  SINGLE context.begin_transaction() — not one transaction per revision. So
  `ALTER TYPE ... ADD VALUE` followed by anything that USES the new value
  (an UPDATE/INSERT/CASE referencing it) fails with Postgres's "unsafe use
  of new value of enum type", and — this is the non-obvious part — putting
  the ADD VALUE in an earlier migration file does NOT fix it: if both
  migrations are pending in the same `alembic upgrade head` invocation
  (e.g. a fresh DB, or CI), they still land in that one shared transaction.
  This only surfaces when a migration needs to USE a value it just widened
  onto an enum (0014's activity_type widen never hit it because it only
  ever added values, never wrote rows with them). The safe pattern: don't
  ADD VALUE at all — rebuild the type. CREATE a new enum with every label
  the column should end up with, `ALTER TABLE ... ALTER COLUMN ... TYPE
  <new> USING (CASE ... END)::<new>` to cast existing rows across via an
  explicit mapping, DROP the old type, then `ALTER TYPE <new> RENAME TO
  <old_name>`. Values are usable immediately because they were present at
  the type's CREATE, not added afterward, so the restriction never applies.
  See 0029_billing_foundation.py for the full worked example (it also drops
  retired labels outright this way, instead of 0014's additive approach of
  leaving them stuck in the DB forever).
- sa.table() REFLECTION DEFAULTS ENUM COLUMNS TO THE WRONG BIND TYPE (billing
  foundation wave, 2026-07-26, migration 0030 — the SECOND time this exact
  class of bug has appeared; migration 0029 hit an adjacent enum issue in
  the same wave). When a migration builds a `sa.table("x", sa.column("tier",
  sa.Text()), ...)` reflection to run `op.bulk_insert()` or `op.execute()`
  against a column that's actually a real Postgres enum (not text), SQLAlchemy
  binds that column's values with an explicit `::VARCHAR` cast — and Postgres
  has no implicit VARCHAR->enum cast for parameterized INSERT or UPDATE, so it
  fails: `column "tier" is of type workspace_plan but expression is of type
  character varying`. This is NOT the same restriction as the ADD VALUE entry
  above (that one is about transaction timing; this one is about SQLAlchemy
  picking the wrong bind type for a reflected column) — but both surface from
  the same underlying habit: reaching for `sa.Text()` as the default type in a
  quick `sa.table()` reflection without checking what the real column type is.
  The fix: declare the reflected column with the SAME `postgresql.ENUM(...,
  create_type=False)` object the table's real DDL uses (not sa.Text()), so
  SQLAlchemy emits the matching bind type. Before writing any migration that
  bulk_inserts, updates, or otherwise reflects a table via sa.table()/
  sa.column(), check whether each touched column is a Postgres enum first —
  see 0029_billing_foundation.py's UPDATE statements (worked around by using
  plain string literals instead of bound params) and 0030_plan_prices.py's
  bulk_insert (worked around by binding the real ENUM type) for both fixes.
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
  ADDENDUM (2026-07-12, migration 0024): automation_log also has a nullable
  `detail` column persisting the REAL failure reason on *_failed rows
  ("no_registered_device", "<provider>: <error>") — the same string the
  operational log line gets. NULL means success/suppression OR a pre-0024 row;
  no backfill on purpose, and the client (feed.ts REASON_NOT_RECORDED) states
  "not recorded" honestly rather than inventing one. The /automation-log API
  exposes channel + detail; digest entries carry null for both.
- THE DEV API SERVER DOES NOT AUTO-RELOAD — START IT WITH --reload (found live
  2026-07-12). The documented startup command lacked the flag, so the :8000
  process served the code imported at its start time FOREVER: an entire evening
  of correct, committed, migrated changes (verifiedCount on /me, GET
  /intake/items/recent, GET /intake/items/{id}) 404'd/missing live while the
  full test suite passed and alembic sat at head. The symptom signature —
  "endpoint exists in code + tests green + migrations at head, but live :8000
  404s" — means the PROCESS is stale, not the code: check the listener's age
  against git log (`Get-NetTCPConnection -LocalPort 8000 -State Listen` → PID →
  `Get-CimInstance Win32_Process` CreationDate/CommandLine; no `--reload` in
  CommandLine = it never picks anything up). Fix: kill the pair (uvicorn parent
  + server child) and start with `uv run python -m uvicorn oryx.main:app --port
  8000 --reload` — watchfiles 1.2.0 is installed so WatchFiles-based reload
  works on Windows; a reload restarts the colocated monoprocess workers too,
  which is correct in dev. The startup memory (project_dev_startup.md) now
  carries the flag. In monoprocess dev there is exactly ONE backend process —
  workers cannot be independently stale.
- REACT-QUERY KEYS ARE A SHARED NAMESPACE, SHAPES INCLUDED (2026-07-12, caught
  in review before it shipped). Two callers using the SAME queryKey must cache
  the SAME data shape — the web search overlay initially cached the raw
  ApiResponse envelope under ['intake','sources'] while useIntakeSources caches
  the unwrapped array there, which would silently corrupt whichever screen read
  second. Rule: never re-declare an existing module's query inline — import and
  reuse its hook (modules/intake/hooks/useIntakeSources.ts is the intake list
  registry).
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

- ff_intake_* FLAGS GATE CLIENT SURFACES ONLY (confirmed 2026-07-11, the
  ff_intake_rss flip). No backend intake endpoint checks any ff_intake_* flag —
  the string appears in backend src ONLY in the FlagKey Literal. POST/GET
  /intake/sources, the Gmail OAuth router, webhooks, and admin manual ingest
  are all live and capability-gated (intake.write / require_platform_admin)
  regardless of flag state; the scheduler polls any enabled source row. So
  flipping an ff_intake_* flag is a UI reveal, not a backend enable — and
  conversely, "flag off" is NOT a server-side safety barrier for intake.
  Client checks are narrower than the flag set: SourceManagementScreen reads
  only ff_intake_rss + ff_intake_gmail; ff_intake_manual gates ManualIngest
  (AND'd with account.isPlatformAdmin); ff_intake_webhook and
  ff_intake_api_pull gate NO client surface at all today.
- RSS FETCHER HAS NO SSRF GUARD (open hardening gap, noted in migration 0023).
  api_pull deliberately built providers/api_pull/safety.py (resolved-IP deny
  list + allowlist) because pull URLs are user-controlled; the RSS provider
  fetches its equally user-controlled feed_url with plain httpx — a workspace
  member with intake.write can point a feed at internal/metadata IPs. Exposure
  exists independent of the ff_intake_rss flag (the endpoint was never
  flag-gated). Follow-up: port the safety guard into rss/client.fetch_feed.
- A TAB-LEVEL NAVIGATE NEVER RESETS A NESTED STACK (two real web-sidebar bugs,
  2026-07-11). `navigationRef.navigate('Tabs', { screen: X })` only FOCUSES tab
  X with whatever nested state it already has — and if X is already focused it
  is a complete no-op (no state event fires, so even the sidebar highlight
  doesn't move). Bug 1: Verification Center originally landed on the Settings
  root (expired sessions went undetected). Bug 2: the Settings root item itself
  used the bare-tab path, so pressing "Settings" from Automation Hub/Analytics/
  Verification stayed put. Convention now enforced by webNav tests: EVERY
  sidebar item targeting the Settings tab names an explicit nested screen, and
  performNav routes all Settings-tab items through navigateSettingsScreen
  (falling back to SettingsHome). The SAME latent class exists for the Research
  and Content sidebar items (bare-tab navigates over stacked tabs — e.g.
  "Content Studio" pressed while deep in DraftEditor stays on DraftEditor);
  flagged 2026-07-11 but out of that wave's scope, fix it the same way when a
  wave touches that area. VERIFIED stat definition decided the same day:
  claims have NO verification_status column — the per-item verdict is
  intelligence_objects.verification_status, and the Command Center stat counts
  'verified' + 'analyst_approved' (approval REPLACES 'verified', so excluding
  it would decrement the stat on review).
- LIVE BROWSER VERIFICATION NEEDS A PRE-EXISTING SIGNED-IN SESSION (2026-07-12,
  design-foundation wave). Expo web persists auth via expo-secure-store →
  localStorage, but tokens expire: a full page reload on a stale token bounces
  to /auth/sign-in, and Claude Code cannot re-authenticate (typing passwords is
  policy-prohibited) — the remaining visual checks then block on the owner
  signing in first. Plan visual waves accordingly: capture EVERY screenshot
  needed early, while the session is alive; in-app navigation keeps a live
  session, full reloads are what kill an expired one. Two related quirks:
  (1) CDP screenshots through the Chrome extension routinely time out once
  ("renderer frozen") right after an action — the immediate retry succeeds;
  (2) to visually prove a deliberately-unwired primitive, mount it via a
  clearly-marked TEMP block in an existing screen, screenshot, then remove the
  block and re-run the suite before committing (done for CardHeader/
  HairlineRowList; Metro hot-reloads the temp block in ~300ms).
- THE BROWSER PAGE CAN RUN A STALE EXPO WEB BUNDLE — CHECK METRO'S "Web
  Bundled" LOG BEFORE TRUSTING ANY LIVE OBSERVATION (2026-07-13, the frontend
  twin of the stale-:8000 trap). A long-lived Expo web tab does NOT reliably
  hot-apply edits (the loaded bundle URL carries hot=false): an entire
  live-verification pass once ran against a bundle predating the wave's
  edits — the "new code doesn't work" observation was false, and a workaround
  (params nonce) was nearly shipped for a defect that did not exist. Symptom
  signature: gates green + Metro running, but live behavior matches PRE-edit
  code. Check: compare the Metro log's last "Web Bundled …" lines against
  when the edits were saved; no new bundle line = stale page. Fix: full
  browser reload — which drops the signed-in session (see the session entry
  above), so expect a re-login and capture screenshots immediately after.
  Corollary: a "fix didn't work" live result must be cross-checked against
  bundle freshness before theorizing about the code.

- LIGHT/DARK THEMING IS LIVE — PHASE A SHAPE (2026-07-16). `themes.dark` /
  `themes.light` live in packages/design-system/src/tokens (lightPalette /
  lightColors / lightGradients in colors.ts; the core light values are
  owner-provided WCAG-verified, the rest derived + contrast-checked — see the
  colors.ts block comment). The switch: Redux theme slice (modeSet) → the
  app's ThemedProvider passes themes[mode] into ThemeProvider; hydration from
  /auth/me preferences.themeMode; the SettingsHome Appearance toggle PATCHes
  /v1/preferences {themeMode} (migration 0025) and patches the ['me'] cache in
  place. FOUR STANDING RULES: (1) the `gx` StyleSheet is STILL static-dark —
  restructuring it is theming Phase B; components consuming gx keep dark
  pockets in light mode by design, don't "fix" one ad hoc. (2) ErrorBoundary
  is PERMANENTLY outside ThemeProvider (its 4 hexes are a deliberate
  exception — it must render when theming itself breaks). (3) statusColors /
  severityColors / draftColors are spec-locked mode-invariant per their own
  headers — never give them light variants without an owner decision.
  (4) Pure tests import tokens from '@oryx/design-system/tokens' (the package
  root pulls react-native and breaks tsx); rendered both-mode tests use the
  shims harness. Trap found live: rendered tests seed PARTIAL ['me'] payloads,
  so any new useMe field read needs a deep optional chain
  (`query.data?.preferences?.themeMode`) or every seeded-cache test crashes.

- REASONING-MODE OPENAI-COMPAT MODELS RETURN 200 WITH EMPTY CONTENT INSIDE
  PIPELINE BUDGETS (diagnosed live 2026-07-22 on NVIDIA NIM Nemotron
  llama-3.3-nemotron-super-49b-v1.5). Such models spend ~900-1000 output
  tokens "thinking" before any content; the pipeline budgets (extractor 800 /
  classifier 50 / detector 200 / linker 150) truncate mid-reasoning, so
  message.content arrives EMPTY on a successful HTTP 200 — all four callers
  parse-fail, the conflict detector silently returns NO_CONFLICT for real
  conflicts, and the circuit breakers count every call as a SUCCESS (parse
  failures are not ProviderErrors). Fix shipped: settings field
  openai_compat_disable_reasoning (env OPENAI_COMPAT_DISABLE_REASONING=1,
  keep it ON for Nemotron/Qwen-class vendors) makes OpenAICompatProvider
  prepend NO_THINK_TOKEN ("/no_think") to the system message ON THE WIRE
  only — the four *_SYSTEM_PROMPT constants and the Anthropic/Ollama paths
  are untouched (pinned by tests in test_ai_provider_openai_compat.py).
  Diagnostic signature to remember: "tokens billed > 0 but parse_failed=True
  on every item, circuits closed" = reasoning mode, not a code bug.
  RESOLVED (2026-07-22 ADR, two-layer fix): parse-failures-on-200 are now
  visible WITHOUT touching breaker semantics. Layer 1: every parse failure at
  the four callers (incl. the classifier's bad-label case — same contract-
  violation class) emits verification.ai.parse_failed (payload callType),
  a post-freeze §3.3 catalog extension mapped to ai_parse_failures_total —
  analytics-only, deliberately ABSENT from the dispatcher's notification
  CATALOG (regression-tested). Layer 2: AIQualityTracker (ai_circuit_breaker
  .py, singleton beside the breaker, same call_type keying, SEPARATE state —
  it can never open a circuit) counts consecutive parse failures per
  call_type and logs `ai_quality.parse_failure_streak` exactly once per
  streak at 5. Count-based on purpose (no clock): a misconfigured model fails
  every call, so wall-clock windows add nothing. When adding a fifth AI
  caller, wire BOTH layers: record_parse_outcome(call_type, ok) at the parse
  site + an AI_PARSE_FAILED emission in the service layer's session.

- "TRUSTED SOURCES" AND "INTAKE SOURCES" ARE TWO UNRELATED ENTITIES DESPITE
  BOTH SOUNDING LIKE "the sources list" (found building source-governance
  tiers, 2026-07-22). TrustedSourcesScreen shows `source_catalog` +
  `workspace_sources` (a pure per-workspace on/off toggle, PK
  (workspace_id, source_key) where source_key is a source_catalog.key
  STRING) — confirmed via grep that `WorkspaceSource` is NEVER read anywhere
  under `services/intake`, so this toggle has ZERO effect on what actually
  gets ingested (matches the existing `ff_intake_*` "client-surface-only"
  gotcha above). The REAL, credibility-bearing entity is `intake_sources`
  (workspace-scoped, real UUID `id`, the thing `source_credibility_records.
  source_id` actually joins against) — a real intake connector (RSS/Gmail/
  webhook/etc.), managed on a completely different screen
  (SourceManagementScreen/SourceCard, reached via IntakeHomeScreen). The two
  are NOT 1:1: a catalog key like `the_block` and a same-named custom RSS
  `intake_sources` row for "The Block" can coexist with zero code link
  between them (`origin_catalog_key` is the only possible bridge, and is
  NULL on every real intake_sources row observed to date — nobody has used
  the catalog-provisions-a-real-connector flow yet). Any feature keyed on
  "real per-source activity/credibility/accuracy" (tiers, conflict counts,
  accuracy history) belongs on the intake_sources side; never fabricate a
  name-based match to bridge them (duplicate names exist for real, e.g. two
  real rows both literally named "NSE India"/"NSE India1").
- THE MOBILE WEB SHELL HAS NO URL FOR MOST NON-SETTINGS-HOME SCREENS
  (found same wave). `navigation/linking.ts`'s Settings sub-tree only listed
  8 of the many real Settings-stack screens (ProfileEdit/ChangePassword/
  ActiveSessions/AlertsSettings/TrustedSources/AutomationHub/Analytics)
  before this wave — IntakeHome/IntakeSourceManagement/IntakeSourceDetail/
  SourceCredibility (and likely others, e.g. verification/intelligence
  detail screens) had NO web URL at all, unreachable except by an in-app tap
  chain that itself often starts from a sidebar item not yet wired for web
  (dimmed nav items, e.g. "Intake Engine", are genuinely inert on click, not
  just visually deemphasized). When a wave needs to verify a screen live and
  the sidebar can't reach it, check `linking.ts` first — a missing URL
  entry is a one-line, safe, mechanical fix (register the EXISTING screen,
  same pattern as every sibling entry), not a sign the screen is broken.
- A SEPARATELY-MANAGED LOCAL uvicorn --reload PROCESS CAN SERVE STALE CODE
  FOR ONE ROUTE WHILE HEALTH-CHECKING FINE (found same wave, unresolved
  root cause). Adding a new response field once showed up correctly via a
  direct in-process ASGI call (`AsyncClient(transport=ASGITransport(app=
  create_app()))`, the same mechanism the integration test suite uses) and
  via a bare `python -c` call into the repository/router functions, but was
  MISSING from the live HTTP response of a manually-started `uv run uvicorn
  --reload` background process — even immediately after a full kill+
  restart, confirmed via `Get-CimInstance Win32_Process`. `Get-NetTCPConnection`
  also intermittently reported an already-dead PID as still owning port 8000
  (confirmed dead via `Get-Process -Id <pid>` erroring) — a stale OS listener-
  table entry, not a real process. When a manually-run dev server disagrees
  with a direct in-process/pytest check for the SAME code, trust the
  in-process check and treat the standalone process as suspect; don't
  conclude the code is wrong from the standalone server alone. Root cause
  not fully diagnosed — flagged here rather than guessed at.

- source_catalog ROWS HAVE REAL FK DEPENDENTS ACROSS THE OWNER'S OWN REAL DEV
  ACCOUNTS — CHECK BEFORE ANY DELETE (found building the RSS catalog
  activation path, 2026-07-22). `workspace_sources.source_key` FKs to
  `source_catalog.key` with NO `ON DELETE` clause (RESTRICT by default), and
  every account the owner actually uses for verification — "Live Verify's
  Workspace", "Oryx's Workspace", "krishna mishra's"/"aman mishra's"/"Yash
  Mishra's Workspace" — had toggled on both the four homepage-only "majors"
  (bloomberg/ft/reuters/wsj) AND, more surprisingly, the `cat-XXXXX` test-
  fixture pollution rows (23 dependents) — the latter because
  FocusAndSourcesScreen's onboarding step shows the ENTIRE real
  `source_catalog` filtered only by `focus`, so test junk that leaked into
  the catalog table got tapped through onboarding right alongside real
  entries, indistinguishable in the UI. A catalog-row DELETE that looks like
  pure cleanup can silently fail (FK violation) or, if cascaded, quietly
  remove real accounts' real toggle choices — confirm dependents with a real
  query (`SELECT w.name, ws.source_key FROM workspace_sources ws JOIN
  workspaces w ON w.id=ws.workspace_id WHERE ws.source_key IN (...)`) and
  get explicit confirmation before cascading, every time, even when the
  catalog row itself is confirmed test pollution.
- source_catalog.url NOW MEANS "the real feed URL", NOT a vendor homepage
  (same wave). Migration 0001's original seed used homepage links
  (bloomberg.com, ft.com, etc.) for every entry — none were ever activatable,
  since providers/rss/config_schema.py's `feed_url` needs an actual feed
  endpoint. Migration 0026 repoints `url` to real, confirmed, live-checked
  RSS endpoints for the entries meant to be real (coindesk, decrypt,
  cointelegraph, yahoo_finance) and removes the ones with no confirmed feed
  (bloomberg/ft/reuters/wsj) rather than leaving `url` semantically split
  between "homepage" and "feed" across different rows. `the_block` was the
  one remaining exception — still homepage-only, deliberately left that way
  pending a confirmed feed URL, not fabricated — until migration 0028 found
  its real feed at `https://www.theblock.co/rss.xml` (live-checked: HTTP 200,
  genuine RSS 2.0; the also-200 `/api/rss` path is a JSON error page, not a
  feed — a reminder that HTTP 200 alone doesn't confirm a feed, check the
  body). Every source_catalog row now has a real, confirmed feed URL — the
  mobile picker's `UNACTIVATABLE_CATALOG_KEYS` exclusion set
  (`catalogPicker.ts`) is currently empty as a result, kept as
  infrastructure since a decorative row has now recurred once already. Any
  future catalog entry must have a real, live-checked feed URL in `url`
  before being added — a
  `pytest.mark.requires_network` test (opt-in via
  `ORYX_ALLOW_NETWORK_TESTS=1`, mirroring `requires_db`) now exists in
  `test_catalog_source_activation.py` to keep proving this as entries change.
- POST /intake/sources' origin_kind='catalog' PATH IS NOW REAL — IT WAS
  PURE UNEXERCISED SCHEMA SURFACE BEFORE (same wave). The request body
  accepted `origin_kind`/`origin_catalog_key` since Phase 3, but recon
  confirmed zero real intake_sources rows anywhere trace an
  `origin_catalog_key` back to a real (non-test-fixture) catalog key — the
  only prior exerciser was `test_credibility_bootstrap.py`'s isolated
  fixture. The endpoint now derives `kind`/`config.feed_url` from the real
  `SourceCatalog` row server-side for this path (never trusting a
  client-supplied feed_url alongside a claimed `origin_catalog_key` — a real
  integrity gap that existed simply because nobody had used the path for
  real yet), while cadence overrides in the request config still pass
  through. The `origin_kind='custom'` path is untouched byte-for-byte
  (regression-tested).
- A "FRESH SIGNUP" SCREENSHOT CANNOT BE CAPTURED VIA BROWSER AUTOMATION —
  EVER (found doing live visual proof for the source-catalog picker rebuild,
  2026-07-23). The safety rules prohibit entering any password into any
  browser field, with no exception for a throwaway test account's own
  brand-new password — so both sign-up and sign-in are equally blocked, not
  just re-authenticating an existing session (contrast the earlier "LIVE
  BROWSER VERIFICATION NEEDS A PRE-EXISTING SIGNED-IN SESSION" entry above,
  which is about session expiry, not this). Any future wave asking for a
  "new signup" or "onboarding" browser screenshot must get that proof
  another way: a real backend integration test driving `/v1/auth/signup` +
  the real endpoints end-to-end (httpx against the ASGI app, no browser),
  plus reusing whatever shared UI component the onboarding screen shares
  with an already-reachable authenticated screen for the actual pixels.
- ESLINT HAS NO `react-hooks/exhaustive-deps` RULE CONFIGURED IN THIS REPO.
  Referencing it in an `// eslint-disable-next-line react-hooks/exhaustive-
  deps` comment is itself a lint ERROR ("Definition for rule ... was not
  found"), not a harmless no-op — found when a new onboarding effect's
  disable comment turned a clean `pnpm lint` into 1 new error. If a
  `useEffect` deps array looks incomplete to a future reviewer, just write
  it correctly (or note the reason in a plain comment) rather than
  suppressing a rule this project's eslint config doesn't run.
- A "known small cost" list item can already be fixed — CONFIRM STATE BEFORE
  FIXING (2026-07-25). Asked to wire WebSidebar's foot profile row to real
  /me data, recon found it already was (`displayName`/initials/workspace
  role, conditionally rendered on real data, no "Jordan Mehta" placeholder)
  — the real remaining work that wave was a NEW regression test
  (WebSidebar.test.tsx) locking in behavior that already shipped, not a
  code fix. Don't assume a task description's premise is still true; quote
  the real current code first.
- A CROSS-TAB `navigation.navigate(tab, {screen})` PUSH NEEDS AN EXPLICIT
  BACK-TARGET, NOT JUST A FORWARD DESTINATION (2026-07-25, companion bug to
  the 2026-07-11 bare-tab-navigate class above). Activity opened
  IntakeItemDetail via `navigate('Settings', {screen: 'IntakeItemDetail'})`
  — a real destination, but back popped to whatever the Settings stack
  already held (SettingsHome), not to Activity, since the push landed on a
  foreign navigator with no memory of where the user came from.
  IntakeItemDetail has 3 real callers (Activity, Dashboard's Today row, web
  search) sharing one registered screen, so the fix couldn't change default
  back behavior for all of them — ActivityHomeScreen now tags its navigate
  with `params: {..., origin: 'activity'}`, and ItemDetailScreen only
  intercepts `beforeRemove` when it sees that origin, redirecting to the
  Activity tab via `navigation.getParent()?.navigate('Activity')`. The
  interception must replay the original `e.data.action` via
  `navigation.dispatch()` after redirecting (guarded by a ref so the replay
  doesn't re-trigger the same preventDefault) — otherwise the Settings
  stack is left stuck on IntakeItemDetail, and a later bare Settings-tab
  press (bottom tab icon, no explicit screen) shows stale item content
  instead of SettingsHome. Same recipe applies to any future "screen with
  multiple real callers, one of which needs a different back target" bug.
- FOUR MORE EXPO PACKAGES NEEDED TEST SHIMS ONCE A COMPONENT TRANSITIVELY
  IMPORTED `store/thunks/auth.ts` (2026-07-25, WebSidebar.test.tsx —
  WebSidebar imports `signout` from that thunk for its workspace menu).
  `expo-secure-store` (lib/secure-store.ts) → `expo-constants` +
  `expo-notifications` (lib/push/expoPushEffects.ts) chain-load
  `expo-modules-core`'s real native module and crash under plain Node, even
  though the shimmed `Platform.OS === 'web'` guard means secure-store's
  real code path is never actually reached in the test. `expo-linear-
  gradient` (WebSidebar's foot/avatar gradient) needed the same inert-host
  shim treatment as `expo-blur`. All four added to
  `src/test/shims/register.js` alongside the existing shims — check that
  file before assuming a new expo-* import can't be rendered under
  `tsx --test`.
- WEB NEVER PERSISTS A REFRESH TOKEN — ANY refreshToken-DEPENDENT FLOW
  SILENTLY NO-OPS AFTER A PAGE RELOAD (found building the Team/Workspace
  switcher, 2026-07-26). `set_session_cookie` (core/security/cookies.py)
  cookies ONLY the access token; the refresh token is handed to the client
  once, in the signin/signup/refresh JSON body, and `store/thunks/auth.ts`
  puts it in Redux (`state.auth.refreshToken`). `bootstrapAuth()`'s web
  branch never repopulates it — it only probes `/auth/me` via the cookie to
  decide authenticated/not. So `state.auth.refreshToken` is real ONLY for
  the tab that just live-completed signin/signup; a page reload, a fresh
  tab, or (critically) opening any deep link from a real email — which is
  indistinguishable from a fresh page load — leaves it `null` and stays
  `null` for the rest of that page's life. This silently breaks the
  EXISTING `/auth/refresh` 401-retry interceptor on web too (pre-existing,
  not introduced by this wave) and broke the new switch-workspace flow
  identically until fixed: `WebSidebar.tsx`'s switch handler and
  `AcceptInviteScreen.tsx`'s "Switch to this workspace now" both now check
  for a missing refreshToken and show an honest inline message ("Switching
  needs a fresh sign-in in this browser tab...") instead of silently doing
  nothing. Any FUTURE web feature that calls a refreshToken-requiring
  endpoint (switch-workspace, /auth/refresh, anything built the same way)
  must plan for this null case explicitly — don't assume Redux has it just
  because the user is "signed in" per the cookie. Fixing the underlying gap
  (e.g. also cookying a refresh token) is an auth-architecture decision, not
  something to slip in inside a feature wave.

- A REAL DEV DB AT A STALE MIGRATION HEAD FAILS SILENTLY AT THE UI LAYER,
  LOUDLY ONLY IN THE SERVER LOG (Team nav promotion wave, 2026-07-26, found
  live). The startup migration-drift check (b403c4c) logs a clear
  `migration.stale_database` warning block when `alembic_version` lags the
  latest head, but that warning is INFO-level server output only — any new
  code path that writes to a table the stale DB doesn't have yet (here: a
  fresh `record_activity()` INSERT into a table added by the wave's own new
  migration) fails the whole request, and the client just shows its generic
  honest-error copy ("Could not send invite") with no hint that the real
  cause is schema drift, not a real validation failure. Symptom signature:
  a brand-new feature 500s or generic-errors on its first live click, full
  test suite is green (tests run against a DB already migrated by CI/the
  test fixture), and the ONLY signal is that stale-database warning block
  buried in the dev server's own stdout. Check `alembic current` (or the
  server log for `migration.stale_database`) before assuming new code is
  broken when it "works in tests but not live."
- A `uvicorn --reload` LOG FILE WRITTEN INSIDE THE WATCHED DIRECTORY CAUSES
  AN INFINITE RELOAD LOOP (same wave, found live while starting the dev
  server for screenshots). Redirecting the server's own stdout/stderr to a
  file under `apps/backend/` (the directory watchfiles watches) makes every
  log line append trigger a `1 change detected` → reload cycle, which then
  logs its own restart lines, feeding itself forever — CPU churns, and any
  request that lands mid-restart fails outright (this is what made the
  migration-drift symptom above look worse than it was, before the real
  cause was found). Always redirect a manually-started dev server's log
  output to a path OUTSIDE any directory the reloader watches (e.g. the
  session scratchpad, or `/tmp`), never to a file inside the watched app
  directory itself.
- THE require-CACHE-PATCH TRICK FOR `useNavigation` ONLY WORKS FOR THE
  FIRST TEST IN A FILE TO REQUIRE THAT SCREEN MODULE (found writing
  TeamHomeScreen.test.tsx, 2026-07-26). AcceptInviteScreen.test.tsx's
  pattern — replacing `require.cache[resolvedPath].exports` with a patched
  `@react-navigation/native` object before `req('./Screen')` — only
  rebinds what a FUTURE `require()` call returns; a screen module's own
  `useNavigation` reference is captured ONCE at its first load (Node's
  module cache means later `renderScreen()` calls in the same test file
  return the ALREADY-loaded module, whose captured reference still points
  at whichever patch object existed the first time it loaded). A test that
  only checks rendered text or that navigation doesn't crash never notices
  this (which is why AcceptInviteScreen.test.tsx's own tests never caught
  it — none of them assert on captured navigate() calls). A test that DOES
  assert `navigateCalls` contents across multiple tests in one file gets a
  silently-empty array. Fix: use `NavigationContext.Provider` with a
  fresh-per-render fake navigation object instead (the pattern
  research/rowNavigation.test.tsx already established) — never the
  require-cache patch — whenever a test needs to actually verify what a
  screen navigated to, not just that it didn't crash.
- EXPO SDK 51's TOP-LEVEL `app.json` "splash" KEY HAS NO LIGHT/DARK VARIANT
  (found closing the long-flagged app.json splash issue, 2026-07-27). The
  classic `expo.splash.{image,backgroundColor}` shape always renders one
  color/image regardless of `userInterfaceStyle` — real per-appearance
  splash values require installing `expo-splash-screen` as an explicit dep
  (`npx expo install expo-splash-screen` — resolves the SDK-51-correct
  0.27.x, not latest) and moving splash config into a `plugins` array entry
  with a sibling `dark: {image, backgroundColor}` object. Before that
  install, "add light-mode splash values" is not achievable via config
  alone — don't fake it by picking one compromise color. Separately: the
  actual app.json/icon assets at the time (splash.png #1A2332,
  icon.png/adaptive-icon.png #0A0A0F) were flat single-color placeholders
  with zero logo/mark — not a stale-but-designed asset, literally a solid
  rectangle. Confirmed pixel-exact via manual PNG decode (Node zlib
  inflate on the IDAT chunk) since no PIL/ImageMagick was available in
  either the backend uv env or bash. Regenerated the same way (zlib
  deflate + hand-built IHDR/IDAT/IEND chunks) rather than pulling in a new
  image lib — fine for flat placeholder color swaps, NOT a substitute for
  real icon/splash artwork (a HornMark or similar) if that's ever wanted.
- A "FROZEN" EXACT-MATCH TEST NEEDS AN EXPLICIT, NAMED WIDENING WHEN A REAL
  POST-FREEZE ADDITION LANDS — DON'T LET IT SILENTLY FAIL (Team Chat
  foundation wave, 2026-07-27). test_notification_dispatcher.py's
  test_catalog_covers_exactly_the_frozen_section_2_events asserts
  `set(CATALOG) == set(FROZEN_SECTION_2)` — a deliberate drift guard against
  the frozen Phase 6 doc. Adding a legitimate new CATALOG entry for a later
  wave (CHAT_MESSAGE_SENT) breaks that exact-match on purpose; the fix is
  NOT to loosen the assertion but to add a small, explicitly-named
  POST_FREEZE_ADDITIONS dict beside FROZEN_SECTION_2 and assert against
  `{**FROZEN_SECTION_2, **POST_FREEZE_ADDITIONS}` — same pattern as widening
  a frozen enum: additive, and named, never silent. Same wave found a sibling
  trap in test_automation_hub_api.py: CATEGORIES/len(grid)==12/len(others)==11
  are separately pinned to the pre-chat 4-category grid and needed their own
  explicit update (to 5/15/14) — grep for a category tuple's exact literal
  member list AND every hardcoded count derived from it before assuming a
  NOTIFICATION_CATEGORIES widen is test-safe.
- RUNNING A MIGRATION AGAINST oryx_test WHILE A BACKGROUND FULL-SUITE PYTEST
  RUN IS STILL IN FLIGHT ON THE SAME DB is a real race worth avoiding, even
  though it happened to complete cleanly this one time (Team Chat foundation
  wave, 2026-07-27: `alembic upgrade head` applying a CREATE TABLE + ALTER
  TYPE ADD VALUE landed mid-run of an already-launched full-suite pytest
  background job on the identical oryx_test connection string). A pure
  additive migration (new table, new enum value) happened not to collide
  with the running suite's queries against pre-existing tables, but a
  migration that ALTERs an existing table's columns while a live suite reads
  that same table could deadlock or observe a half-migrated schema. Always
  let an in-flight full-suite background run finish (or stop it first, e.g.
  via TaskStop) before applying a new migration to the same test database —
  don't rely on "it happened to be safe" repeating.
- types.py's "THIS FILE IS GENERATED — DO NOT EDIT" HEADER IS STALE (Team
  Chat UI wave, 2026-07-27). `pnpm gen:pydantic` / `drift:check` (same
  script, infra/scripts/gen-pydantic.ts) does NOT generate the file — its
  own top comment says so: "Phase 2: the type catalog outgrew that
  approach. The pydantic file is now maintained as a *committed mirror*."
  The script only verifies (a) every shared-types source is listed and
  present, (b) types.py parses as Python, (c) every TS string-literal
  union has an identically-named, identically-membered Python `Literal`.
  It does NOT check that non-Literal shapes (interfaces/response models)
  match — removing a whole unused response type from workspaces.ts and
  running gen:pydantic produced zero diff and zero error, because nothing
  in the check inspects non-Literal type bodies. Fixing this class of
  drift means hand-editing types.py to match the TS source, then running
  drift:check only to confirm the Literal unions still agree — the check
  is a partial guardrail, not proof the mirror is otherwise correct.
- THE REAL DEV DATABASE (`anant`) HAS THE SAME TEST-FIXTURE POLLUTION
  PROBLEM AS source_catalog, BUT FOR WORKSPACES (found seeding Team Chat
  screenshots, 2026-07-27). `SELECT count(*) FROM workspaces` on the real
  dev DB returned 971 rows, the overwhelming majority named "Test User's
  Workspace" / "Admin WS" / "Claims WS" etc. — leftover from prior
  integration-test runs that were pointed at this DB instead of a
  dedicated oryx_test at some point. Separately and more surprising: `kind`
  is `'personal'` on EVERY SINGLE ROW, including the owner's real,
  actively-used, multi-member workspaces (e.g. "Live Verify's Workspace",
  which has a real owner + admin + editor). `kind='team'` has never once
  been set anywhere in this database. Nothing in the codebase currently
  reads `Workspace.kind` to gate multi-member behavior (confirmed: chat,
  invites, member list, activity all work identically regardless of
  `kind`) — treat `kind` as a cosmetic/future-facing label only, never as
  a signal for "does this workspace have real members," and don't be
  surprised that seeding a second real member into a `kind='personal'`
  workspace works fine end-to-end.
- KeyboardAvoidingView WAS MISSING FROM THE RN TEST SHIM (same wave).
  `src/test/shims/react-native.js` aliases the platform layer to inert
  host components for `tsx --test` rendering (see the 2026-07-14/07-25
  entries above for the pattern), but had never needed
  `KeyboardAvoidingView` until TeamChatScreen wrapped its compose bar in
  one — any screen using it crashes under the render-test harness with an
  "element type is invalid" error until it's added. Added as
  `host('KeyboardAvoidingView')`, same one-line pattern as every other
  entry; check this file before assuming a real RN component can't be
  rendered under the harness.

- A COMPONENT THAT GATES CHROME ON auth.status MUST ALSO CHECK FOR A
  PUBLIC/UNAUTHENTICATED ROUTE, INDEPENDENTLY (Public Reader Rev 1 frontend
  wave, 2026-08-03). RootNavigator's new public-route branch (a genuinely
  unauthenticated /public/pages/:slug screen, reachable before auth.status
  is even read — see rootNavigatorDecision.ts) mounts alongside WebShell,
  which wraps the ENTIRE navigator tree and had its own, separate
  `showChrome = status === 'authenticated' && me.data?.onboarding?.state
  === 'complete'` check with no notion of "are we on a public route" at
  all. Consequence: an already-signed-in visitor opening a public link in
  the same browser tab would have seen their own sidebar/topbar wrapped
  around the public page — auth.status alone can't tell you the route is
  public, since the visitor genuinely IS authenticated. Fixed by having
  WebShellInner call the SAME usePublicPageRoute() hook RootNavigator uses
  and AND-ing `!publicRoute.isPublicRoute` into showChrome. Any FUTURE
  top-level chrome (a global banner, a different shell wrapper) must repeat
  this same AND, not assume RootNavigator's own branching is sufficient
  protection — WebShell sits OUTSIDE RootNavigator's component tree
  entirely (App.tsx: `<WebShell><RootNavigator/></WebShell>`), so it has no
  visibility into which branch RootNavigator picked.
- WebSidebar/webNav.ts READ SEVERAL /me FIELDS WITH ONLY ONE LEVEL OF
  OPTIONAL CHAINING (found writing a rendered WebShell test, same wave).
  `me?.profile.displayName`, `me?.build.version`, and webNav.ts's
  `navCounts()` (`me?.verification.pendingReviewCount`, `me?.content.
  draftCount`, `me?.activity.unreadCount`) all guard only the `me?`
  itself — a seeded /me fixture missing `profile`/`build`/`verification`/
  `content`/`activity` crashes the render with "Cannot read properties of
  undefined", it does not fall back to a blank/zero display. Any test that
  renders WebSidebar (directly, or indirectly via WebShell with chrome
  showing) needs the FULL MeResponse shape — copy WebSidebar.test.tsx's own
  `ME` fixture rather than hand-rolling a minimal one.
- RENDERING WebShell ITSELF (not just WebSidebar) UNDER THE tsx TEST
  HARNESS NEEDS A `document` STUB TOO (same wave, first user:
  WebShellPublicRouteIsolation.test.tsx). WebShellInner's ⌘K-overlay effect
  calls `document.addEventListener('keydown', ...)` unconditionally on web
  — plain Node has no `document` global, so a minimal
  `{addEventListener, removeEventListener}` stub is required in addition to
  the existing `window` stub pattern. Install both ONCE at module load and
  never delete them between tests in the same file: WebSidebar's own async
  `['workspaces']` query can resolve (or a stray effect can fire) after a
  test's synchronous assertions return, and deleting the globals between
  tests raced that trailing async work — a later effect referencing an
  already-deleted `document` crashed a DIFFERENT test than the one that
  triggered it ("Attempted to capture a commit phase error inside a
  detached tree"). Mutate `window.location.pathname` in place per test
  instead of recreating the global.
- A LOCAL DEV PORT CAN BE SQUATTED BY A COMPLETELY UNRELATED, NON-ORYX
  PROCESS (found starting the backend for live verification, same wave).
  `netstat`/`Get-NetTCPConnection` showing something LISTENING on :8000
  does not mean it's a stale ORYX uvicorn process from an earlier session —
  `Get-CimInstance Win32_Process` on the PID can reveal a totally different
  application (seen here: a `venv\Scripts\python.exe -m uvicorn app.main:app
  --reload --reload-exclude=app.db*` process — SQLite-based, unrelated repo
  entirely). Never kill a port-holding process on the strength of the port
  number alone; check its real CommandLine first. The safe move when it's
  genuinely unrelated is to start ORYX's backend on a different port
  (`--port 8001`) and point Expo web at it via `apps/mobile/.env`'s
  `EXPO_PUBLIC_API_BASE_URL` (gitignored, safe to leave/regenerate) rather
  than touch a process that isn't this project's.

## What This Skill Deliberately Does NOT Contain

Current phase/wave status, current commit hashes, current test counts.
These change too fast to hardcode safely. Check memory, ask the user, or
read the actual repo/report in front of you. Treat any phase-status claim
in this file as instantly stale if found — there shouldn't be one.
