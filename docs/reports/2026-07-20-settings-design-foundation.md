# Settings adopts the design foundation (ST-1..ST-5) — completion report

Commits: `92ab78a9c6d0ae4e54876544b62d0b02719e0b48` —
`feat(settings): Settings adopts the design foundation (ST-1..ST-4)`;
`869f8a51f5d75da7f0ebd9e569f441505588537f` —
`fix(settings): ST-5 — Verification row's icon glyph used the surface-only teal accent`
(found during Phase 3 visual proof, below); report commit `ccee4886e6cc2fde6937f9e65a398b7afbedd2f7`
plus this update.

## Phase 0 — confirm current state

**No ST-1 through ST-6 recon document exists.** Before touching any code I
searched the repo, full git history (`git log --all --grep`), and the
project's persistent memory for "ST-1", "ST-2"..."ST-6", "recon", and
"settings" — nothing. This matches a previously-recorded gotcha
(`chat_handoff_attachments_missing` memory): a Claude Chat task prompt refers
to prior work product that never actually arrived. Per that precedent, I did
not fabricate quotes attributed to a document I don't have. Instead, Phase 0
below is fresh recon directly against the real current code, which is a more
reliable source than a stale/absent document in any case.

**Real current Settings sections**, as they exist in
`apps/mobile/src/modules/settings/` today (quoted, with file:line):

1. **Account/Profile** — `SettingsHomeScreen.tsx:69-90` (pre-wave): identity
   card (name/email) + a single "Edit profile" row → `ProfileEditScreen.tsx`
   (two stacked `AuthFormField`s, no grid).
2. **Appearance** — `SettingsHomeScreen.tsx:92-109` (pre-wave): inline
   dark/light `ChoiceTile` toggle, live since Theming Phase A
   (`fd7bb85`, `preferences.themeMode`, migration 0025).
3. **Security** — `SettingsHomeScreen.tsx:111-136` (pre-wave): "Change
   password" row → `ChangePasswordScreen.tsx` (two `AuthFormField`s); "Active
   sessions" row → `ActiveSessionsScreen.tsx` (one `Card` per session,
   `borderRadius: 8` on the icon well — a token violation, see Phase 2); a
   footnote about AES-256-GCM.
4. **Alerts** — `SettingsHomeScreen.tsx:138-149` (pre-wave): "Notification
   preferences" row → `AlertsSettingsScreen.tsx` (per-category `ChoiceTile`
   frequency picker + quiet-hours preset picker).
5. **Automation** — `SettingsHomeScreen.tsx:151-170` (pre-wave): two rows
   linking to `AutomationHubScreen` and `AnalyticsHomeScreen` — both owned by
   other modules with their own already-shipped design-foundation waves
   (AH-1..AH-4 `5c22f5f`, AN-2/AN-3 `d0cba49`). Out of scope here; only the
   link row itself is a Settings surface.
6. **Sources** — `SettingsHomeScreen.tsx:172-191` (pre-wave): "Trusted
   sources" row → `TrustedSourcesScreen.tsx` (flat `ChoiceTile` list of the
   source catalog); "Source intake" row links to the `intake` module (its own
   future wave).
7. **Verification** — `SettingsHomeScreen.tsx:193-204` (pre-wave): one row
   linking to `VerificationQueueScreen` (`verification` module, own scope).

**The task's assumed desktop-only constructs do not exist in the built app.**
The task named "the two-column form grid, the session table, the source
table mentioned in project history" as out-of-scope desktop anatomy to defer.
I traced this to `docs/design-reference/screens/settings.jsx` — the
aspirational Genspark web mockup, not built code. That file has a
`gridTemplateColumns: '160px 1fr'` field grid (Profile tab), an
`<table className="tbl">` session table (Security tab, with MFA + an Audit
log the app has never built), and an `<table className="tbl">` source-trust
table with tiers/verified/conflicts columns (Sources tab) — plus Billing,
API-token, and Admin tabs that don't exist in the router at all
(`SettingsStack.tsx`). None of this reached the real React Native code: every
built Settings screen is already single-column, Card/`ChoiceTile`-based, with
zero `<table>`/CSS-grid anatomy anywhere (`grep -rn "tbl\|table\|grid"
apps/mobile/src/modules/settings/` → 0 structural matches). Confirmed
further by the design-system's own Phase B changelog
(`packages/design-system/src/styles/genspark.ts`, uncommitted, not part of
this wave): `tblHeadCell`/`tblCell` were retired as gx keys specifically
because they had **zero runtime consumers**.

**Section-by-section portability classification** (evidence-based, not
assumed from the task's premise):

| Section | Classification | Why |
|---|---|---|
| Profile (identity + edit link) | Fully portable | Single-column, no grid |
| Appearance | Fully portable, already foundation-compliant | `ChoiceTile` = Card + real typography + tokens already |
| Security (password + sessions) | Fully portable | No table; sessions was one-card-per-row, migrated this wave |
| Alerts (nav link) | Fully portable | Simple row |
| Alerts preferences (sub-screen) | Fully portable, already foundation-compliant | `ChoiceTile`-based |
| Automation (nav links) | Fully portable; screens themselves out of module scope | Link rows only |
| Sources (nav links) | Fully portable | Link rows only |
| Trusted sources (sub-screen) | Fully portable, already foundation-compliant | `ChoiceTile`-based |
| Verification (nav link) | Fully portable | Single row |

**No genuinely desktop-only table/grid exists anywhere in the real Settings
code to defer.** This is the one finding that overrides the task's premise:
there was no hidden desktop mega-table screen to work around, so this wave
covers every real Settings screen rather than artificially limiting scope.

## Phase 1 — foundation applied to portable sections

- `apps/mobile/src/modules/settings/components/SettingsRow.tsx` — stripped
  its own `Card` wrapper (rows now live inside a parent `HairlineRowList`,
  matching the `WorkspaceCard`/RW-1 precedent). `SettingsRow` is used only by
  `SettingsHomeScreen.tsx` (confirmed via repo-wide grep), so this was safe.
- `apps/mobile/src/modules/settings/screens/SettingsHomeScreen.tsx` — the six
  navigation-row sections (Profile, Security, Alerts, Automation, Sources,
  Verification) rebuilt through `Card` + `CardHeader` + `HairlineRowList`,
  replacing the pre-migration one-card-per-row `SettingsRow` and the
  hand-typed `Text variant="caption"` ALL-CAPS section labels. The Profile
  card now groups the identity summary and the "Edit profile" row under one
  `CardHeader title="Profile"`. The Security card carries
  `CardHeader sub="AES-256-GCM"`.
- `apps/mobile/src/modules/settings/screens/ActiveSessionsScreen.tsx` — the
  session list rebuilt the same way: `Card` + `CardHeader title="Sessions"
  sub={deviceCountSub(...)}` + `HairlineRowList`. New pure presenter
  `apps/mobile/src/modules/settings/sessions.ts` (`deviceCountSub`) mirrors
  the `workspaceCountSub` precedent (silent while loading, pluralizes,
  states a real zero).

**Deliberately deferred, not silently skipped:**

- **Appearance** (inline in `SettingsHomeScreen.tsx`), **Alerts
  preferences** (`AlertsSettingsScreen.tsx`), and **Trusted sources**
  (`TrustedSourcesScreen.tsx`) keep their current `ChoiceTile` anatomy. Each
  `ChoiceTile` is itself a `Card` — its border and selection dot ARE the
  selected-state affordance — so folding these into `HairlineRowList` would
  either strip that visual cue or require editing the shared `ChoiceTile`
  component, which is also used by the onboarding module (outside Settings,
  outside this wave's remit). These three screens already satisfy "the
  established foundation" at the row level (Card primitive, real typography
  variants — `h2`/`bodySm` — and token colors), so the gap was only the
  section-label typography, and CardHeader cannot be used standalone outside
  a Card without misaligning its 12px horizontal padding against Screen's
  own edge padding (verified against `CardHeader.tsx` and how it's used
  elsewhere — always inside a `Card`'s `header` slot). Pinned by test
  (`foundation.test.ts`: "deferred honestly: Appearance,
  Alerts-preferences, and Trusted Sources keep their ChoiceTile anatomy").
- **ProfileEditScreen.tsx** and **ChangePasswordScreen.tsx** are plain forms
  (stacked `AuthFormField`s + one `Button`) — there is no row/list anatomy in
  either screen to migrate. Pinned by test.
- **AutomationHub, Analytics, IntakeHome (Source intake), VerificationQueue**
  are screens owned by other modules with their own dedicated waves (or
  future waves for intake/verification) — only the Settings link row to each
  was touched, never the destination screen. Pinned by test.

## Phase 2 — token violation sweep

Two real violations found and fixed, same pattern as the RW-3/AH-4
precedents:

- `apps/mobile/src/modules/settings/components/SettingsRow.tsx:59` (pre-wave)
  — `iconWrap` carried `borderRadius: 8` as a hardcoded literal. On-scale
  for `radius.xl` (8), but the AH-4 precedent's test rejects **any**
  numeric `borderRadius` literal, not just off-scale ones. Fixed →
  `borderRadius: t.radius.xl`.
- `apps/mobile/src/modules/settings/screens/ActiveSessionsScreen.tsx:95`
  (pre-wave) — identical `borderRadius: 8` violation on the session-row icon
  well. Fixed → `t.radius.xl`.

No hex or `rgba()` literals were found in any Settings file (confirmed via
`grep -rn "borderRadius:\s*\d|#[0-9a-fA-F]{3,8}|rgba?\("
apps/mobile/src/modules/settings/` before and after).

**Found but explicitly NOT fixed (out of scope):**
`apps/mobile/src/modules/auth/components/AuthFormField.tsx:54` carries
`borderRadius: 10` — genuinely off-scale (not in `radius`/`gensparkRadius`
at all). `AuthFormField` is imported by `ProfileEditScreen.tsx` and
`ChangePasswordScreen.tsx` (in-scope) but lives in the `auth` module and is
also used by sign-in/sign-up (out of scope — "do not touch any screen
outside Settings"). Flagged here for a dedicated auth-module or
cross-cutting token-sweep wave; not fixed in this commit.

## Phase 3 — visual proof: DONE (initially blocked, then unblocked by the owner)

Both dev servers were already running (backend :8000, Expo web :8081). On
first attempt, navigating to `http://localhost:8081` redirected to
`/auth/sign-in` with no existing session — typing a password is
policy-prohibited, matching the previously-recorded
`live_browser_verification_needs_session` gotcha. Work paused there and the
owner was asked to sign in. **The owner signed in** and confirmed; in-app
navigation (clicking the gear icon, not a reload) then reached Settings with
the session intact.

**Breakpoint confirmation** (the "don't reuse 576 blindly" check):
`SIDEBAR_COLLAPSE_BREAKPOINT` (576 = 232px sidebar + 344px
`MIN_CONTENT_WIDTH`) is a single global constant driving the whole web
shell's sidebar collapse (`webShellLayout.ts`), derived from Command
Center's KPI-tile floor. Settings' own content — single-line label/
description rows with a trailing chevron, no fixed-width tiles — has a
genuinely smaller minimum than that KPI-tile floor. Confirmed live at
576×900: the sidebar correctly collapses to the hamburger, and every row
stays fully readable with no wrapping/overlap/truncation — 576 holds without
needing to be raised.

**Shots captured** (all real, via `mcp__claude-in-chrome`):
1. Settings home, desktop (1280×900), dark — Profile/Appearance/Security.
2. Settings home, desktop, dark, scrolled — Alerts/Automation/Sources/
   Verification (post-fix, see ST-5 below).
3. Settings home, desktop, **light** mode — Profile/Appearance/Security
   (confirms token-driven theming: cards, borders, and text correctly
   invert; the sidebar itself stays dark by design — the `gx` StyleSheet is
   documented as still static-dark, Theming Phase B territory, not this
   wave's scope).
4. Settings home, desktop, light, scrolled — Alerts/Automation/Sources/
   Verification (post-fix).
5. Settings home, narrow (576×900), dark — Profile/Appearance/Security.
6. Settings home, narrow, dark, scrolled — Alerts/Automation/Sources/
   Verification (post-fix).
7. Active Sessions screen, desktop, dark — confirms the `CardHeader
   title="Sessions" sub="54 DEVICES"` real pluralized count and
   `HairlineRowList` rows render correctly against real data (54 real
   session rows).

**ST-5 — a real bug found during this phase, fixed on the spot.** The
Verification row's icon well rendered as a blank box with zero visible
glyph, in both themes. Traced via `Icon`'s color resolution
(`packages/design-system/src/components/Icon.tsx`) to `accent="teal"` on
that row → `t.colors.accent.teal`, which `tokens/colors.ts` documents as
**SURFACE-ONLY** (fills/washes; 1.49:1 contrast vs bg in dark; a near-white
`#E3EFFA` wash in light) — never meant for icon/text glyphs, which should
use `semantic.positiveText` instead. `Icon`'s `color` prop has no path to
`semantic.positiveText`, so the scoped, Settings-only fix was to swap the
row's accent to `"coral"` (a real glyph-safe accent — resolves to violet
`#8B5CF6`/`l.violet`, already used elsewhere on this screen).
Repo-wide grep confirmed this `accent="teal"`/`color="teal"` icon-glyph
usage was the **only** one anywhere in the mobile app — fully self-contained
to this one Settings row, so fixing it stayed within this wave's scope.
Pinned by a new test. Commit `869f8a5`.

**False alarm, investigated and ruled out:** the Active Sessions screen's
per-row `Icon name="Smartphone" color="brand"` also looked like a blank box
in a normal-resolution screenshot. DOM inspection (`elementFromPoint`,
computed style, and a precise pixel-region zoom) confirmed the SVG renders
correctly — correct 20×20 size, correct `stroke="#5B5BF5"` indigo, fully
opaque and visible — it was just a thin 1.75px stroke that a
downscaled/compressed full-page screenshot washes out. No code change was
needed; this is a screenshot-fidelity limitation, not an app defect.

## Tests

New: `apps/mobile/src/modules/settings/sessions.test.ts` (1 test),
`apps/mobile/src/modules/settings/foundation.test.ts` (9 tests, one added
for the ST-5 fix) — both registered in `apps/mobile/package.json`'s explicit
test-file list (no glob support on this runner).

Named tests:
- `deviceCountSub stays silent while loading, states a real zero plainly, and pluralizes`
- `token sweep: no hardcoded hex/rgba color or hardcoded borderRadius survives in the touched Settings files`
- `the fixed icon wells route through the real radius token (radius.xl, the prior 8px value)`
- `SettingsHomeScreen groups every navigation-row section under CardHeader + HairlineRowList`
- `SettingsRow no longer wraps itself in its own Card — it is a bare row for a parent HairlineRowList`
- `ActiveSessionsScreen groups sessions under a real CardHeader with the pluralized device-count sub`
- `deferred honestly: Appearance, Alerts-preferences, and Trusted Sources keep their ChoiceTile anatomy`
- `deferred honestly: ProfileEdit and ChangePassword stay plain forms — no row/list anatomy exists to migrate`
- `ST-5 fixed: no Settings row uses the surface-only teal accent as an icon glyph color`
- `out of scope, not part of this Settings module: AutomationHub/Analytics/IntakeHome/VerificationQueue rows only link out`

## Full suite before/after

A pre-existing, unrelated "Theming Phase B" restructure
(`packages/design-system/src/styles/genspark.ts` and consumers in
automation/content/dashboard/research/web-shell) was already sitting
uncommitted in the working tree when this wave started — it is not part of
either commit and was left untouched (staged and committed only the
Settings-scoped files by name; the shared `package.json` test-script line
was reconstructed to include only the pre-wave baseline plus this wave's two
new files for the first commit, then the working tree was restored
afterward so Phase B's pending edit isn't lost; the ST-5 fix commit needed
no `package.json` change).

- **True before-baseline** (`git stash`'d to the exact pre-wave state,
  including Phase B's pending edits, then tested): 192 passed / 0 failed.
  `pnpm type-check` clean.
- **This wave's own contribution**: +10 tests (`sessions.test.ts` ×1,
  `foundation.test.ts` ×9) — 192 → 202 on top of clean pre-wave `HEAD`.
- **After** (full working tree, both this wave's commits plus the
  still-uncommitted, unrelated Phase B work): 209 passed / 0 failed.
  `pnpm type-check` clean. `pnpm drift:check` clean (40 string-literal
  unions match). `pnpm lint`: 35 warnings / 0 errors (pre-existing
  `sort-imports` pattern; two of the warnings are this wave's own touched
  files, consistent with the ~36-warning baseline the project already
  carries — not a new error class).

## Commits

- `92ab78a9c6d0ae4e54876544b62d0b02719e0b48` —
  `feat(settings): Settings adopts the design foundation (ST-1..ST-4)`
  (7 files: `SettingsRow.tsx`, `SettingsHomeScreen.tsx`,
  `ActiveSessionsScreen.tsx`, `sessions.ts`, `sessions.test.ts`,
  `foundation.test.ts`, `package.json`).
- `ccee4886e6cc2fde6937f9e65a398b7afbedd2f7` — `docs(reports): Settings
  design-foundation wave completion report` (this report, first version).
- `869f8a51f5d75da7f0ebd9e569f441505588537f` — `fix(settings): ST-5 —
  Verification row's icon glyph used the surface-only teal accent`
  (2 files: `SettingsHomeScreen.tsx`, `foundation.test.ts`).
- This report's update (Phase 3 completed, ST-5 documented) is committed
  separately, following the project convention of never amending.

## New/updated memory and skill files

None required. This report documents a wave-specific correction (the
absent ST-1..ST-6 recon, and the design-reference-vs-built-code gap for
Settings specifically); it is not a new recurring operational gotcha beyond
the two already recorded in
`.claude/skills/oryx-architect/SKILL.md` ("chat handoff attachments
missing" and "live browser verification needs a pre-existing signed-in
session"), both of which this wave's Phase 0 and Phase 3 independently
re-confirmed still hold.
