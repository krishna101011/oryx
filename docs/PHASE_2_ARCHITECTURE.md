# Anant Capital — Phase 2 Architecture (FROZEN)

**Phase:** 2 — Identity, Access, Preferences, Control Plane
**Status:** FROZEN — 2026-06-06
**Revision:** 2 (incorporates 6 change requests)
**Depends on:** Phase 1
**Unblocks:** Phase 3 (Intake), Phase 4 (Verify/Analyze), Phase 5+

> Phase 2 is the *control plane*. Identity, workspace, preferences, alert rules, and feature gates.
> Implementation begins only after this document is signed off. No further architectural changes without an explicit unfreeze.

---

## Change Log — Revision 2

| # | Change | Where it lands |
|---|---|---|
| 1 | MFA reduced to interface-only (DB fields + contracts + flag retained; UI, flows, screens removed) | §2.2, §8.2, §9.2, §10, §11 |
| 2 | Onboarding collapsed from 7 steps to 4 | §4 |
| 3 | Provider layer inserted between service and repository | §8.1, §8.3, new appendix |
| 4 | Settings surface reduced to Profile / Security / Alerts / Trusted Sources | §5, §9.2 |
| 5 | New ADR-014: Event Architecture (sync, async, queue, domain events, pub/sub) | `docs/adr/ADR-014-event-architecture.md` |
| 6 | "Notifications" renamed "Activity" throughout product, code, and DB | §6, §8, §9, §10, §11 |

**Why these changes improve maintainability:**

- **MFA deferral** halves the auth surface area for Phase 2 without losing the option to ship it later — the DB columns and feature flag stay so we never need a migration to enable it.
- **Onboarding compression** cuts a 7-step funnel to 4. Cold-start completion rate is the single biggest driver of activation in intelligence products; fewer steps = fewer drop-off points.
- **Provider layer** establishes the contract for every Phase 3+ vendor integration. Adding Gmail, Notion, Claude, or push providers later becomes "add one folder" instead of "refactor the service".
- **Settings reduction** removes ~7 screens we'd otherwise carry as locked or half-built UI. Each removed screen had no Phase 2 business logic behind it.
- **Event architecture ADR** locks in how Phase 4's verification, Phase 5's publishing, and Phase 6's notifications will communicate — before they're built. Removes a class of future refactors.
- **Activity rename** prevents the cognitive collision of having a "Notifications" tab that never sends notifications. "Activity" is honest about what Phase 2 actually does.

---

## 1. Product Explanation for Phase 2

### 1.1 What Phase 2 Does

- Real authentication: sign up, sign in, sign out, refresh, session management
- Account, profile, and workspace model — every user belongs to exactly one workspace from day 1
- Preferences and trust settings the rest of the product reads from (focus areas, content style, verification strictness, trusted sources)
- Alert preferences (model and storage only — delivery is Phase 6)
- Feature flags that gate every later phase's surfaces
- Compressed 4-step onboarding wizard
- Reduced settings surface: Profile, Security, Alerts, Trusted Sources
- An `/v1/auth/me` envelope that returns account + profile + workspace + preferences + flags + activity unread count in one call
- A provider abstraction layer for all future external integrations
- An event architecture (ADR-014) that later phases plug into

### 1.2 What Phase 2 Does NOT Do

- Working MFA — interface only; no UI, no flows
- Gmail OAuth, IMAP, label parsing — **Phase 3**
- RSS, market data, crypto data — **Phase 3**
- AI summarization, scoring, clustering — **Phase 4**
- Verification engine — **Phase 4**
- Research persistence, content drafts, publishing — **Phase 4–5**
- Alert *delivery* (push, email) — **Phase 6**
- Team/multi-user workspaces with invites — designed for, not built
- Billing, plans, paid tiers — **Phase 7+**
- Theme picker, language/region UI, delete-account flow, integrations page, about pages

### 1.3 Why This Phase Is Needed Now

1. **Every later phase scopes data to a user and workspace.** Without stable identity, every later table is rewritten when we add auth.
2. **Trust settings shape Phase 4's verification engine behavior.** Building verification before defining policy produces a feature without rules.
3. **Feature flags are how Phases 3–8 ship incrementally.** Adding flags after launch is always retrofitted poorly.
4. **The provider abstraction defines how every Phase 3+ vendor is plugged in.** Defining it now prevents vendor lock-in from the first integration onward.

### 1.4 Why Other Features Are Deferred

| Deferred | Phase | Why not now |
|---|---|---|
| Full MFA flows | Patch release after 2 | Auth complexity should stay bounded; contracts kept so enable is non-breaking |
| Gmail intake | 3 | Requires identity (here) + provider layer (here) |
| Verification engine | 4 | Requires trust policy (here as preferences) |
| AI summaries | 4 | Requires verified inputs |
| Content drafts | 5 | Requires analyzed inputs |
| Publishing | 5 | Requires drafts |
| Push/email delivery | 6 | Preferences stored here; delivery is a separate concern |
| Team invites | Later | Workspace primitive ships here; invites are additive |

---

## 2. User System Architecture

### 2.1 The Four Primitives

```
┌──────────────┐    1:1     ┌──────────────┐
│   ACCOUNT    │ ─────────► │   PROFILE    │
│  (identity)  │            │ (presentation)│
└──────┬───────┘            └──────────────┘
       │
       │ M:N via workspace_members
       ▼
┌──────────────┐
│  WORKSPACE   │   ← All later domain rows scope here
│ (data scope) │
└──────────────┘

       ┌──────────────┐
       │   SESSION    │   1:N per account
       │  (presence)  │
       └──────────────┘
```

| Concept | Answers | Why separated |
|---|---|---|
| Account | "Who is this?" | Auth lifecycle independent of presentation |
| Profile | "How do they show up?" | Editable without touching auth |
| Workspace | "Whose data is this?" | All later domain rows scope here |
| Session | "Are they logged in now?" | Many sessions per account; individually revokable |

### 2.2 Auth Model (MFA interface-only)

- **Email + password** as the primary credential
- **Argon2id** for password hashing
- **Short-lived access token** (JWT, 15 min) + **rotating refresh token** (opaque, 30 days)
- Refresh tokens stored as **SHA-256 hashes** in the `sessions` table
- Bearer token in `Authorization: Bearer <jwt>`; refresh token stored client-side in Expo SecureStore
- **MFA: interface only.** The `mfa_enabled` column, the `mfa_secret` column, the `MfaSetup` shared-type, the feature flag `ff_mfa`, and the route stubs all exist; the actual setup/verify/disable handlers return `501 NOT_IMPLEMENTED` for now. No mobile UI. When MFA ships later, no migration is needed and no contract is broken.
- **Rate limiting** on `/v1/auth/signin` and `/v1/auth/signup` (5 attempts / 10 min per IP + per email)
- **Account lockout** after 10 consecutive failed sign-ins
- All auth events written to immutable `auth_audit_log`

**Why interface-only beats "remove it entirely":** if we delete the columns and contract today, enabling MFA later requires a destructive migration on a production table. Keeping the columns nullable, the contract present, and the flag off means we ship MFA later as a pure feature add.

### 2.3 Account Model

```
accounts
─────────────────────────────────────────────────────────────────
id                  uuid       pk
email               citext     unique, not null
email_verified_at   timestamp  nullable
password_hash       text       not null    (argon2id encoded)
password_changed_at timestamp  not null
status              enum       ('pending', 'active', 'suspended', 'deleted')
mfa_secret          text       nullable    (encrypted at rest; reserved)
mfa_enabled         bool       default false                       (reserved)
failed_login_count  int        default 0
locked_until        timestamp  nullable
last_login_at       timestamp  nullable
created_at          timestamp
updated_at          timestamp
deleted_at          timestamp  nullable
```

### 2.4 Profile Model

```
profiles
─────────────────────────────────────────────────────────────────
account_id      uuid     pk, fk → accounts.id
display_name    text     not null
avatar_url      text     nullable
headline        text     nullable
timezone        text     not null    (IANA; backend uses for time math; no UI to change in Phase 2)
locale          text     not null    (BCP-47; same: backend reads, no UI in Phase 2)
created_at      timestamp
updated_at      timestamp
```

### 2.5 Workspace Model

Every account gets a default workspace at signup. All later domain rows scope by `workspace_id`, not `account_id`.

```
workspaces
─────────────────────────────────────────────────────────────────
id                uuid     pk
name              text     not null
kind              enum     ('personal', 'team')
owner_account_id  uuid     fk → accounts.id, not null
plan              enum     ('free', 'pro', 'enterprise')
created_at        timestamp
updated_at        timestamp
deleted_at        timestamp nullable

workspace_members
─────────────────────────────────────────────────────────────────
workspace_id      uuid     fk → workspaces.id
account_id        uuid     fk → accounts.id
role              enum     ('owner', 'admin', 'editor', 'reader')
invited_by        uuid     fk → accounts.id, nullable
joined_at         timestamp
removed_at        timestamp nullable
pk (workspace_id, account_id)
```

### 2.6 Session Model

```
sessions
─────────────────────────────────────────────────────────────────
id                  uuid       pk
account_id          uuid       fk → accounts.id
refresh_token_hash  text       unique not null   (sha-256 hex)
parent_session_id   uuid       fk → sessions.id, nullable  (rotation chain)
device_id           text       not null
device_label        text       not null
device_platform     enum       ('ios', 'android', 'web')
ip_address          inet       nullable
user_agent          text       nullable
created_at          timestamp
last_used_at        timestamp
expires_at          timestamp
revoked_at          timestamp  nullable
revoked_reason      text       nullable
```

Rotation, reuse detection, "sign out everywhere" unchanged from Revision 1.

---

## 3. Permission and Role Architecture

### 3.1 Phase 2 Reality: Single-User Mode

Every workspace has one member: its owner. The permission system *runs* on every request even though it never denies anything yet — so Phase 4 doesn't ship the first real check broken.

### 3.2 Future Team Mode (designed, not built)

| Role | Can do |
|---|---|
| `reader` | Read all workspace data |
| `editor` | Reader + create research, drafts, content |
| `admin` | Editor + manage members, settings, sources, integrations |
| `owner` | Admin + billing, delete workspace, transfer ownership |

### 3.3 Permission Model

Role-based with capability mapping. Each route declares its required capability via a `require()` dependency. In Phase 2 all paths pass (one role, all wildcards).

### 3.4 Admin Permissions

`is_platform_admin: bool` on the account row. Never elevated except via explicit support tooling.

### 3.5 Access Boundaries

| Boundary | Enforced where |
|---|---|
| Account isolation | `/v1/users/:id` requires `id == current_account.id` |
| Workspace isolation | Every domain query joins on `workspace_id = active_workspace_id` |
| Role-level writes | `require("...")` dependency on every write route |
| Session isolation | `/v1/sessions` filtered to `account_id = current_account.id` |
| Platform admin isolation | Never exposed in product APIs |

---

## 4. Onboarding Architecture (4 STEPS — REVISED)

### 4.1 Compressed Flow

```
NEW SIGN-IN
   │
   ▼ (server checks onboarding_state)
   │
   ┌─────────────────────────────────────────────┐
   │  4 steps, each resumable, each saved on POST│
   ├─────────────────────────────────────────────┤
   │ STEP 1  Welcome + value proposition         │
   │ STEP 2  Focus Areas + Source Preferences    │
   │ STEP 3  Notifications + Permissions         │
   │ STEP 4  Verification Strictness + Style     │
   └─────────────────────────────────────────────┘
   │
   ▼  (write onboarding_completed_at)
HOME / DASHBOARD (placeholder)
```

### 4.2 Step Detail

| # | Screen | What it captures | Writes to |
|---|---|---|---|
| 1 | Welcome | nothing — sets expectations | `onboarding_state.current_step = 'focus_sources'` on tap |
| 2 | Focus Areas + Sources | `focus ∈ {markets, crypto, both}` + custom topics + default trusted source set | `preferences.focus`, `preferences.custom_topics`, `workspace_sources[]` |
| 3 | Notifications + Permissions | `notification_frequency ∈ {off, daily, weekly}` + push permission ask | `preferences.notification_frequency`, device row if permission granted |
| 4 | Strictness + Style | `verification_strictness ∈ {loose, balanced, strict}` + `content_style ∈ {concise, balanced, detailed}` | `preferences.verification_strictness`, `preferences.content_style` |

After step 4, `onboarding_state.completed_at = now()` and the user lands on Home.

### 4.3 Resumability

Each step's POST is durable and idempotent. If the user closes the app between steps, `/v1/auth/me` on next launch returns the resume target. A new device install resumes correctly.

### 4.4 Source Selection inside Step 2

- Focus area picked first inside the same screen
- Curated default trusted sources auto-selected for that focus
- User can deselect; can add custom URL (creates a `workspace_custom_sources` row tagged `pending_verification` — Phase 3 actually fetches and verifies)

### 4.5 Trust / Strictness in Step 4

Same three-tier policy as Revision 1: `loose` / `balanced` (default) / `strict`. Stored in `preferences`. Phase 4 reads it.

### 4.6 Tradeoffs

| Tradeoff | Revision 1 | Revision 2 (current) |
|---|---|---|
| Steps | 7 | 4 |
| Estimated completion time | ~90 sec | ~40 sec |
| Field granularity | High | Compressed but functionally equivalent |
| Drop-off surface | 7 transition points | 4 |

We lose nothing functionally — every preference still gets captured. We just collect related answers on the same screen.

---

## 5. Settings Architecture (REDUCED SURFACE)

### 5.1 Reduced Surface — Phase 2 Settings Tree

```
SETTINGS
├── Profile
│     ├── Display name, avatar, headline
│     └── Email (read-only; change via verification flow, deferred)
├── Security
│     ├── Change password
│     ├── Active sessions list + per-session revoke
│     └── Sign out everywhere
├── Alerts
│     ├── Notification frequency (off / daily / weekly)
│     ├── Per-type frequency (security always on)
│     └── Quiet hours
└── Trusted Sources
      ├── Trusted sources list (enable/disable)
      ├── Confidence overrides per source
      └── Add custom source (creates `pending_verification` row)
```

### 5.2 Removed from Phase 2 (no longer in scope)

| Removed | Why | Where it returns |
|---|---|---|
| Language & Region UI | No real localization until Phase 6+; backend reads timezone/locale fields, no UI needed | Future i18n phase |
| Theme picker | Dark-only in Phase 2; cosmetic accent options add 1 screen for ~0 value | Optional cosmetic patch |
| About pages | No legal text yet to display; placeholders add maintenance burden | Compliance phase |
| Delete account flow | Destructive flow needs auditing, retention policy, and backup story — none of those exist yet | Compliance / billing phase |
| Integrations page | All integrations are Phase 3+; flag-gated tiles add UI to maintain with no underlying functionality | Phase 3 ships this screen with real tiles |

The Phase 2 UI surface shrinks meaningfully: ~7 fewer screens, ~3 fewer settings endpoints, no MFA-related screens at all.

### 5.3 Read/Write Model

Each settings screen reads from one endpoint, writes via PATCH with a partial body, invalidates `/v1/auth/me` and the specific settings key. Optimistic updates not used in Phase 2 (security risk on alert/source changes outweighs UX win).

---

## 6. Activity Architecture (RENAMED from Notifications)

### 6.1 Naming Decision

"Notifications" implied delivery. Phase 2 delivers nothing. The user-facing concept is renamed **Activity** — a feed of things that have happened. The settings section that controls *future* delivery is named **Alerts**. Both names survive into Phase 6 when delivery ships.

Vocabulary lock-in:

| Concept | Name |
|---|---|
| The in-app feed | **Activity** |
| The preferences for future delivery | **Alerts** |
| The mobile module | `activity/` |
| The backend service | `activity/` |
| The mobile tab | "Activity" |
| The settings section | "Alerts" |

### 6.2 Activity Types (Phase 2 emits only security)

```ts
type ActivityType =
  | 'security'         // sign-ins, password changes, session revokes (Phase 2 uses)
  | 'system'           // app updates, welcome (Phase 2 uses sparingly)
  | 'instant_alert'    // Phase 4+ defines
  | 'daily_digest'     // Phase 6
  | 'weekly_digest'    // Phase 6
```

### 6.3 Channels

```ts
type Channel = 'in_app' | 'push' | 'email'
```

Phase 2 writes only `in_app`. `push` / `email` exist as stored preferences for Phase 6.

### 6.4 Permission Handling

- Push permission requested only after onboarding step 3 explains why
- If denied, no re-prompt — only a deep link to system settings
- Email opt-in is a preference, not a system permission

### 6.5 Alert Preferences

```
alert_preferences
─────────────────────────────────────────────────────────────────
account_id   uuid     fk → accounts.id
type         enum     (activity types above)
channel      enum     (channels above)
frequency    enum     ('off', 'instant', 'daily', 'weekly')
quiet_hours  jsonb    nullable
updated_at   timestamp
pk (account_id, type, channel)
```

### 6.6 Device Registration

```
alert_devices
─────────────────────────────────────────────────────────────────
id              uuid     pk
account_id      uuid     fk → accounts.id
platform        enum     ('ios', 'android', 'web')
push_token      text     unique not null
app_version     text
last_seen_at    timestamp
disabled_at     timestamp nullable
```

### 6.7 Activity Inbox

```
activity_inbox
─────────────────────────────────────────────────────────────────
id            uuid       pk
account_id    uuid       fk → accounts.id
workspace_id  uuid       fk → workspaces.id, nullable (security events have no workspace context)
type          enum       (activity types)
title         text
body          text       nullable
data          jsonb      default '{}'   (e.g. session id, ip)
read_at       timestamp  nullable
created_at    timestamp
```

Phase 2 inserts security and system events. Phase 4+ inserts content-related events.

---

## 7. Feature Flag Architecture

### 7.1 Flag Catalog (Revised)

```
ff_settings             default ON
ff_dashboard            default ON     (placeholder; Phase 4 fills)
ff_activity             default ON     (Phase 2 inbox active)
ff_mfa                  default OFF    (MFA interface exists; UI flag-gated)
ff_research             default OFF    (Phase 4)
ff_intake_gmail         default OFF    (Phase 3)
ff_intake_rss           default OFF    (Phase 3)
ff_intake_webhook       default OFF    (Phase 3)
ff_verification         default OFF    (Phase 4)
ff_content_drafts       default OFF    (Phase 5)
ff_publishing_notion    default OFF    (Phase 5)
ff_automation           default OFF    (Phase 6)
ff_push_delivery        default OFF    (Phase 6)
ff_email_delivery       default OFF    (Phase 6)
ff_analytics            default OFF    (Phase 7)
ff_training             default OFF    (Phase 8)
ff_team_workspaces      default OFF    (future)
```

### 7.2 Resolution Order

1. Per-account override
2. Per-workspace override
3. Global default

### 7.3 Phase Gating

Every nav entry and protected screen on mobile is wrapped in `<FeatureGate flag="ff_...">`. Backend routes guarded by flags return `403 FEATURE_DISABLED`.

---

## 8. Backend Architecture for Phase 2

### 8.1 The Four-Layer Architecture (NEW — Change 3)

Every service that touches an external system follows this layered shape:

```
router  ─────►  service  ─────►  provider  ─────►  repository
(HTTP)         (business)        (vendor adapter)   (storage)
```

| Layer | Responsibility | Knows about |
|---|---|---|
| `router` | HTTP parsing, response shaping | FastAPI, schemas |
| `service` | Business rules, orchestration | Other services, providers, repositories |
| `provider` | Talk to one vendor / external system | Vendor SDK only |
| `repository` | Persist and retrieve domain objects | DB driver / ORM only |

#### Why the provider layer exists

Before this layer, vendor SDKs would leak into service code. Six months later, swapping FCM for OneSignal means editing every service that sends push. With this layer:

- `PushProvider` is a tiny interface with `send(token, payload) -> Result`
- `FcmPushProvider` and `OneSignalPushProvider` are interchangeable implementations
- Service code depends on the interface, never the implementation
- Dependency injection (FastAPI `Depends`) wires the concrete provider at startup

#### Provider responsibilities

1. Speak one vendor's language; never the others
2. Translate vendor errors into our canonical `ProviderError` taxonomy (`TRANSIENT`, `PERMANENT`, `RATE_LIMITED`, `AUTH`, `UNKNOWN`)
3. Add retry / circuit-breaker behavior expected from the vendor
4. Emit observability metrics (latency, error rate)
5. NEVER touch the database
6. NEVER touch other vendors

#### Repository responsibilities (unchanged from Phase 1)

1. Translate storage rows into domain models
2. Hide the choice of database from services
3. NEVER make HTTP calls
4. NEVER contain business rules

#### Phase 2 provider stubs

Phase 2 itself uses providers only as interface stubs (no real vendor calls). Real implementations land in their respective phases:

```
services/auth/providers/email/base.py            # interface
services/auth/providers/email/log_only.py        # Phase 2 stub: logs, no send
                                                  # Phase 6: sendgrid.py / resend.py / etc.

services/activity/providers/push/base.py          # interface
services/activity/providers/push/log_only.py     # Phase 2 stub
                                                  # Phase 6: fcm.py
```

This means Phase 2 ships the *pattern*, not the integrations. Phase 3 (Gmail) is the first real provider implementation.

### 8.2 Service Folder Layout (with provider layer)

```
apps/backend/src/anant/services/
├── auth/
│   ├── router.py
│   ├── service.py
│   ├── providers/
│   │   └── email/
│   │       ├── base.py
│   │       └── log_only.py
│   ├── repository.py
│   ├── schemas.py
│   └── security/        # password, JWT helpers
├── accounts/
├── profiles/
├── workspaces/
├── preferences/
├── sources/             # workspace source catalog and selection
├── activity/            # renamed from notifications
│   ├── router.py
│   ├── service.py
│   ├── providers/
│   │   └── push/
│   │       ├── base.py
│   │       └── log_only.py
│   ├── repository.py
│   └── schemas.py
├── feature_flags/
├── onboarding/
└── (settings is a composer in router land — no service folder)
```

### 8.3 Endpoint Catalog (with Phase 2 changes)

**Auth** — MFA endpoints are interface stubs returning `501 NOT_IMPLEMENTED` until `ff_mfa` and matching implementation ship.

| Method | Path | Status |
|---|---|---|
| POST | `/v1/auth/signup` | Active |
| POST | `/v1/auth/signin` | Active |
| POST | `/v1/auth/refresh` | Active |
| POST | `/v1/auth/signout` | Active |
| POST | `/v1/auth/signout-all` | Active |
| GET  | `/v1/auth/me` | Active |
| POST | `/v1/auth/password/change` | Active |
| POST | `/v1/auth/password/forgot` | Active (logs only; real send in Phase 6) |
| POST | `/v1/auth/password/reset` | Active |
| POST | `/v1/auth/mfa/setup` | **Stub (501)** |
| POST | `/v1/auth/mfa/verify` | **Stub (501)** |
| POST | `/v1/auth/mfa/disable` | **Stub (501)** |

**Profiles, Workspaces, Preferences, Sources** — as Revision 1.

**Activity** (renamed)

| GET | `/v1/activity/inbox` | In-app feed (Phase 2: security + system events) |
| POST | `/v1/activity/inbox/:id/read` | Mark item read |
| GET/PATCH | `/v1/activity/alerts/preferences` | Per-type, per-channel frequency |
| POST | `/v1/activity/devices` | Register push token |
| DELETE | `/v1/activity/devices/:id` | Remove a device |

**Sessions, Feature Flags, Onboarding** — paths unchanged from Revision 1; onboarding step enum compressed.

### 8.4 Middleware (unchanged from Revision 1)

```
RequestIDMiddleware
TimingMiddleware
CORSMiddleware
GZipMiddleware
RateLimitMiddleware
AuthMiddleware
WorkspaceContextMiddleware
AuditMiddleware
ErrorHandlingMiddleware
```

### 8.5 Auth Internals

JWT HS256, claims `{sub, wsp, iat, exp, jti}`. Refresh stored hashed. Clock skew 30s.

### 8.6 Logging & Audit

Unchanged from Revision 1. Every auth event hits both structured log and `auth_audit_log`.

---

## 9. Frontend Architecture for Phase 2

### 9.1 Module Folders (with renames)

```
apps/mobile/src/modules/
├── auth/             # NO MFA screens
├── onboarding/       # 4 screens only
├── activity/         # renamed from notifications/
├── settings/         # reduced to 4 sections
└── (Phase 1 modules unchanged)
```

### 9.2 Screen Inventory (final)

**Auth Stack**

- `SignInScreen`
- `SignUpScreen`
- `ForgotPasswordScreen`
- `ResetPasswordScreen` (deep-link target)

**Onboarding Stack (4 screens)**

- `WelcomeScreen` (step 1)
- `FocusAndSourcesScreen` (step 2)
- `NotificationsAndPermissionsScreen` (step 3)
- `StyleAndStrictnessScreen` (step 4)

**Settings Module**

- `SettingsHomeScreen` (4-section list)
- `ProfileEditScreen`
- `ChangePasswordScreen`
- `ActiveSessionsScreen`
- `AlertsSettingsScreen`
- `TrustedSourcesScreen`

**Activity Module**

- `ActivityInboxScreen`

**Removed in this revision (vs Revision 1)**

- `MfaChallengeScreen`, `MfaSetupScreen`
- `ThemeSettingsScreen`, `LanguageRegionScreen`
- `IntegrationsScreen`, `AboutScreen`, `DeleteAccountScreen`
- Onboarding screens 3, 5, 6, 7 from Revision 1 (merged into 4-step flow)

### 9.3 Navigation Flow

```
RootNavigator
├── if (!auth.token)
│     └── AuthStack
├── else if (me.onboarding.state != 'complete')
│     └── OnboardingStack (4 screens)
└── else
      └── RootTabNavigator
            ├── Home
            ├── Research        (ff_research)
            ├── Content         (ff_content_drafts)
            ├── Activity        (ff_activity)        ← renamed tab
            └── Settings        (ff_settings)
```

### 9.4 Auth State (Redux Slice)

```
auth: {
  accessToken: string | null;
  refreshToken: string | null;
  accountId: string | null;
  status: 'unknown' | 'authenticated' | 'unauthenticated' | 'refreshing';
}
```

No `mfaRequired` flag in Phase 2 (interface is dormant).

### 9.5 API Client

Reads access token, attaches `X-Workspace-Id`, attaches `X-Request-Id`. On `AUTH_TOKEN_EXPIRED` → `/v1/auth/refresh` → retry once. On refresh failure → dispatch sign-out, route to `AuthStack`.

### 9.6 FeatureGate Component

```
<FeatureGate flag="ff_intake_gmail" fallback={<ComingSoonTile name="Gmail" />}>
  <GmailIntakeScreen />
</FeatureGate>
```

---

## 10. Database Additions for Phase 2 (Revised)

### 10.1 Renames Applied

- `notification_preferences` → `alert_preferences`
- `notification_devices` → `alert_devices`
- `notification_inbox` → `activity_inbox`

### 10.2 Tables (full Phase 2 net-new)

| Table | Purpose |
|---|---|
| `accounts` | Identity (renamed from Phase 1's `users`) |
| `profiles` | Presentation |
| `workspaces` | Data scope |
| `workspace_members` | Account ↔ workspace |
| `sessions` | Active logins with rotation chain |
| `auth_audit_log` | Immutable auth event log |
| `preferences` | Per-account UX + trust prefs |
| `source_catalog` | Curated sources shipped with app |
| `workspace_sources` | Per-workspace source enable + confidence override |
| `workspace_custom_sources` | User-added URLs (Phase 3 verifies) |
| `alert_preferences` | Per-type/channel frequency (delivery in Phase 6) |
| `alert_devices` | Push tokens |
| `activity_inbox` | In-app feed |
| `feature_flags` | Flag definitions |
| `feature_flag_overrides` | Per-account / per-workspace overrides |
| `onboarding_state` | Per-account resume state with compressed step enum |

### 10.3 Preferences (extended for compressed onboarding)

```
preferences
─────────────────────────────────────────────────────────────────
account_id              uuid     pk, fk → accounts.id
focus                   enum     ('markets', 'crypto', 'both')
content_style           enum     ('concise', 'balanced', 'detailed')
verification_strictness enum     ('loose', 'balanced', 'strict')
notification_frequency  enum     ('off', 'instant', 'daily', 'weekly')
custom_topics           jsonb    default '[]'
created_at              timestamp
updated_at              timestamp
```

### 10.4 Onboarding State (compressed enum)

```
onboarding_state
─────────────────────────────────────────────────────────────────
account_id        uuid     pk, fk → accounts.id
current_step      enum     ('welcome', 'focus_sources', 'notifications_permissions', 'style_strictness', 'complete')
completed_at      timestamp nullable
started_at        timestamp
updated_at        timestamp
```

### 10.5 Indexes

Unchanged: email unique, refresh_token_hash unique, partial indexes on revoked_at/deleted_at, btree on workspace_members.account_id, unique on `feature_flag_overrides (scope, scope_id, flag_key)`, btree on `auth_audit_log (account_id, created_at desc)`.

### 10.6 Migration Tool

Alembic. Every schema change is a migration file. No raw SQL in app code.

---

## 11. Shared Contracts

### 11.1 Type Files in `packages/shared-types/`

```
src/auth.ts                # SignupRequest, SigninRequest, TokenPair, MeResponse
                           # MfaSetupRequest, MfaVerifyRequest  (contracts only)
src/accounts.ts            # Account
src/profiles.ts            # Profile, UpdateProfileRequest
src/workspaces.ts          # Workspace, WorkspaceMember, Role
src/preferences.ts         # Preferences, UpdatePreferencesRequest
src/sources.ts             # SourceCatalogEntry, WorkspaceSource, WorkspaceCustomSource
src/activity.ts            # ActivityItem, ActivityType  (was notifications.ts)
src/alerts.ts              # AlertPreference, Channel, Frequency, Device  (was notifications.ts)
src/feature-flags.ts       # FlagKey, FlagSet
src/sessions.ts            # Session, DevicePlatform
src/onboarding.ts          # OnboardingState, OnboardingStep (4 values), OnboardingStepResult
```

### 11.2 Canonical `MeResponse`

```ts
interface MeResponse {
  account: { id: string; email: string; status: AccountStatus; emailVerified: boolean };
  profile: Profile;
  workspace: { id: string; name: string; kind: 'personal' | 'team'; role: Role };
  preferences: Preferences;
  activity: { unreadCount: number };
  flags: FlagSet;
  onboarding: { state: OnboardingState; nextStep: OnboardingStep | null };
  serverTime: string;
  build: { version: string; commit: string };
}
```

### 11.3 Error Codes

```
AUTH_REQUIRED                401
AUTH_INVALID_CREDENTIALS     401
AUTH_TOKEN_EXPIRED           401
AUTH_REFRESH_INVALID         401
AUTH_REFRESH_REUSE_DETECTED  401
AUTH_EMAIL_TAKEN             409
AUTH_PASSWORD_WEAK           422
AUTH_RATE_LIMITED            429
AUTH_ACCOUNT_LOCKED          423
AUTH_MFA_REQUIRED            401   (reserved; never returned in Phase 2)
AUTH_MFA_INVALID             401   (reserved; never returned in Phase 2)
PERMISSION_DENIED            403
FEATURE_DISABLED             403
WORKSPACE_NOT_FOUND          404
VALIDATION_FAILED            422
ONBOARDING_REQUIRED          409
NOT_IMPLEMENTED              501   (MFA endpoints in Phase 2)
PROVIDER_ERROR               502   (vendor failure surfaced through provider layer)
```

### 11.4 Settings Contract Rules

1. Every PATCH accepts a partial body; missing fields unchanged
2. Validation server-authoritative; client validates for UX only
3. PATCH returns the new full settings object
4. Audit-relevant changes (password, sessions) write to `auth_audit_log`

### 11.5 Permission Rules

1. Every write endpoint declares one capability
2. Every read endpoint is account- or workspace-scoped
3. No role check inline — always via `require()` dependency
4. Capability check runs after auth + workspace context middleware, before the handler

### 11.6 Provider Contract Rules (new)

1. Service code imports the provider *interface*, never the concrete vendor module
2. Concrete providers register via dependency injection in `main.py` startup
3. Every provider call returns a typed `Result<T, ProviderError>`; services never see raw vendor exceptions
4. Providers emit `provider.<vendor>.<op>` metrics (latency, success, error code)

---

## 12. Implementation Plan

### 12.1 Strict Build Order

```
 1. shared-types — full Phase 2 set (auth, accounts, profiles, workspaces, preferences,
    sources, activity, alerts, feature-flags, sessions, onboarding)
 2. Alembic baseline + Phase 2 migrations (accounts, profiles, workspaces, sessions,
    preferences, source_catalog, workspace_sources, workspace_custom_sources,
    alert_preferences, alert_devices, activity_inbox, feature_flags,
    feature_flag_overrides, auth_audit_log, onboarding_state)
 3. core/security/passwords.py (argon2id)
 4. core/security/jwt.py (claims, sign, verify)
 5. Provider base interfaces: EmailProvider, PushProvider + LogOnly impls
 6. services/auth — signup, signin, refresh, signout, password change/forgot/reset
    MFA endpoints scaffolded as 501 stubs
 7. services/accounts, services/profiles, services/workspaces — atomic signup wiring
 8. services/preferences, services/sources — read/write endpoints
 9. services/activity — alerts preferences, devices, inbox (security events only)
10. services/feature_flags — resolver + admin override endpoint
11. services/onboarding — 4-step state machine
12. /v1/auth/me composer
13. Middleware wiring: rate limit, auth, workspace context, audit
14. Mobile — api client + auth slice + SecureStore
15. Mobile — AuthStack (SignIn, SignUp, Forgot, Reset)
16. Mobile — RootNavigator decision logic
17. Mobile — OnboardingStack (4 screens, config-driven)
18. Mobile — Settings (4 sections, 6 screens)
19. Mobile — Activity inbox screen
20. Mobile — FeatureGate component wrapping every flagged surface
21. Tests — see §12.4
22. Security pass — see §12.5
```

### 12.2 Dependency Order Justification

- `shared-types` first because all later code is typed by them
- Migrations before backend code so ORM and types align
- Provider interfaces before services so services depend on the interface, never a concrete vendor
- Auth before any composer because `/v1/auth/me` requires it
- Mobile RootNavigator after `/v1/auth/me` exists so it has something to read
- Activity before Settings because Alerts settings reference the activity preferences shape

### 12.3 What Gets Coded First (top 5)

1. `core/security/passwords.py` with property tests
2. `core/security/jwt.py` with claim-shape tests
3. Alembic migration 0001 (accounts, profiles, workspaces, sessions)
4. Provider interfaces (EmailProvider, PushProvider) + LogOnly implementations
5. `POST /v1/auth/signup` end-to-end: creates account + workspace + workspace_member atomically; returns TokenPair

### 12.4 What Gets Tested First

Ordered by catastrophic-if-wrong:

1. Password hashing (verify, params)
2. JWT signing & verification
3. Refresh rotation + reuse detection chain revocation
4. Workspace creation atomicity (signup transaction)
5. Permission `require()` deny path returns `PERMISSION_DENIED`
6. Feature flag resolution order (account > workspace > global default)
7. Provider interface contract (LogOnly providers exercised in tests)
8. Onboarding step durability across device switch
9. Rate limit + lockout
10. MFA stub returns 501 cleanly (no information leak)

### 12.5 Security Pass

- Rate limits verified under burst
- Lockout verified after 10 fails; resets on successful reset
- Refresh reuse → chain revoke logged with `reuse_detected` reason
- PII redaction verified across all log lines
- CORS origins constrained
- JWT signing key rotation drill documented

### 12.6 Phase 2 Exit Checklist

- [ ] Signup creates account + workspace + member atomically
- [ ] Signin returns access + refresh; access expires 15 min; refresh rotates
- [ ] Refresh reuse triggers chain revocation + audit log
- [ ] `/v1/auth/me` returns full envelope in one round trip
- [ ] 4-step onboarding resumes on a fresh device install
- [ ] Settings (Profile, Security, Alerts, Trusted Sources) persist and re-read
- [ ] Activity inbox renders security events
- [ ] Feature flags resolve to cataloged defaults
- [ ] MFA endpoints return 501 with clean error envelope; no UI references them
- [ ] All provider calls go through the interface; no direct vendor SDK use anywhere except inside `providers/<vendor>/`
- [ ] Sign out everywhere revokes every session
- [ ] No PII in logs
- [ ] CI green: lint, type-check, drift check, tests, security check

---

## Appendix A — ADRs to Land This Phase

1. `ADR-008-argon2id.md` — password hashing choice
2. `ADR-009-token-strategy.md` — JWT access + opaque refresh + rotation
3. `ADR-010-workspace-from-day-one.md` — single-user workspace primitive
4. `ADR-011-flag-resolution.md` — account → workspace → global order
5. `ADR-012-onboarding-resumability.md` — server-side step state, 4 steps
6. `ADR-013-shared-me-envelope.md` — single bootstrap response
7. `ADR-014-event-architecture.md` — sync, async, queue, domain events, pub/sub *(see separate file)*
8. `ADR-015-provider-layer.md` — vendor abstraction interface contract
9. `ADR-016-mfa-interface-only.md` — keep contracts, defer implementation
10. `ADR-017-activity-rename.md` — naming separation of Activity vs Alerts

---

## Appendix B — Out of Scope (defended)

If any of the below appears in a Phase 2 PR, it gets reverted:

- MFA UI, MFA setup flow, MFA verification flow
- Theme picker, language/region UI, integrations page, about pages, delete-account flow
- Onboarding screens beyond the 4 defined
- Any Gmail / OAuth provider client code
- Any RSS / market / crypto data fetching
- Any AI client (summarization, scoring, embeddings)
- Any verification rule code
- Any content draft / publishing logic
- Any push or email *delivery* code (preferences only; LogOnly providers acceptable)
- Any team invite / multi-member workflows
- Any billing / subscription code

---

*This document is the Phase 2 contract, frozen at Revision 2 on 2026-06-06. Implementation may proceed. Deviations require an explicit unfreeze and a new revision.*
