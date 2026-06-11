# Anant Capital — Phase 1 Architecture

**Phase:** 1 — Foundation Only
**Status:** Architecture & Implementation Plan (no code yet)
**Date:** 2026-06-06
**Audience:** Founders, future engineers, future contractors. This is the contract.

> Phase 1 builds the *foundation*. It does not build the product.
> Every later phase depends on the boundaries set here. We over-invest in clarity now so we never refactor the floor later.

---

## 1. Executive Overview

### 1.1 What Phase 1 Includes

- A monorepo skeleton that holds the mobile app, backend service, and shared packages
- A React Native (Expo + TypeScript) **shell** — navigable, themed, no real data
- A Python (FastAPI) **backend skeleton** — routers, settings, logging, health endpoints, no business logic
- A **shared types** package — single source of truth for API contracts, mirrored into pydantic
- A **premium design system** — tokens, typography, primitives, surface rules
- A **navigation map** wired with placeholder screens for every future module
- A **database sketch** for the users domain (Phase 2 will execute against it)
- An **API structure** with versioning, error format, and pagination contracts defined
- **Config and logging skeletons** ready to accept secrets, observability, and tracing later
- A documented **implementation plan** with strict build order

### 1.2 What Phase 1 Excludes

These belong to later phases and will be rejected in Phase 1 PRs:

- Authentication and authorization logic (Phase 2)
- Database migrations and ORM concrete code (Phase 2)
- Gmail intake, OAuth, IMAP, label parsing (Phase 3)
- RSS, webhook, market data, crypto data integrations (Phase 3+)
- AI summarization, clustering, confidence scoring (Phase 4)
- Verification workflows (Phase 4)
- Content drafts, Notion sync, publishing pipelines (Phase 5)
- Charts, tickers, candles, real dashboards (Phase 4+)
- Analytics warehouse, BI dashboards (Phase 7+)
- Notifications (push, email, in-app) (Phase 6)
- Training/education product surfaces (Phase 8)

### 1.3 Success Criteria

Phase 1 is done when **all** of these are true:

1. `pnpm install` at repo root installs every workspace
2. `pnpm mobile:dev` boots Expo and every placeholder screen is reachable from the nav shell
3. `pnpm backend:dev` boots FastAPI; `GET /v1/health` returns 200; `/v1/docs` shows every service router
4. `pnpm type-check` passes across `shared-types`, mobile, and (via mypy) backend
5. `pnpm lint` passes
6. CI runs lint, type-check, and shared-types drift check on every PR
7. A new engineer can clone the repo and reach a running mobile + backend in under 10 minutes following the README
8. The design system tokens are referenced by every primitive — no hard-coded colors or sizes anywhere
9. This document and every ADR are committed and current

### 1.4 Risks

| Risk | Mitigation |
|---|---|
| Scope creep into Phase 2/3 work | Explicit exclusion list above; PR template forces a phase tag |
| Design drift between FE and BE | `shared-types` is the source of truth; CI fails on pydantic-mirror drift |
| Premature DB choice locks us in | Repository interfaces in Phase 1; concrete DB in Phase 2 |
| Premium feel degrades over time | Design tokens enforced via lint rule; no inline colors permitted |
| State management chaos as modules grow | Three-bucket rule documented and enforced in code review |
| Monorepo CI gets slow | Acceptable in Phase 1 (~2 apps). Add Turborepo only when CI exceeds 5 min |
| Architectural decisions get forgotten | Every major decision lives in `docs/adr/` as a permanent record |

### 1.5 Tradeoffs

| Decision | Cheaper alternative | Why we paid more |
|---|---|---|
| Monorepo | Two repos | Shared contracts trivially in sync; atomic cross-cutting PRs |
| TypeScript-first contracts → generated pydantic | OpenAPI codegen | FE devs write contracts in their native language; drift caught at PR time |
| Expo managed | Bare React Native | OTA updates + dev tooling for free; eject only if needed |
| FastAPI | Django | Async-first for AI/streaming workloads; pydantic-everywhere |
| Redux Toolkit + React Query split | Zustand only | Verification flows need devtools, time travel, audit traceability |
| Repository abstraction in Phase 1 | Pick Postgres now | Domain isn't stable enough to commit to a schema yet |
| `services/<domain>/` vertical slices | Layered MVC | Adding a new domain = drop a folder, not a refactor |
| No charts, no AI, no real screens | "Ship something real fast" | Phase 1 proves the *floor*; later phases prove the product |

---

## 2. Product Architecture

### 2.1 Why this section exists

Before any system architecture, we have to agree on what the *product* is doing end-to-end. Without it, engineers optimize parts in isolation and the seams ship broken.

### 2.2 Canonical User Flow (target product)

```
SIGN IN
   │
   ▼
HOME / DASHBOARD ───────────────────────────────┐
   │                                            │
   ├─► INTAKE      (Gmail, RSS, APIs)           │
   │       │                                    │
   │       ▼                                    │
   ├─► VERIFY     (source confidence, dedupe)   │
   │       │                                    │
   │       ▼                                    │
   ├─► ANALYZE    (clustering, summaries)       │
   │       │                                    │
   │       ▼                                    │
   ├─► CREATE     (drafts, research notes)      │
   │       │                                    │
   │       ▼                                    │
   └─► PUBLISH    (Notion, web, social) ────────┘
       │
       ▼
   NOTIFICATIONS  (push, digest, alerts)
```

In Phase 1 every node is a placeholder screen. The point of drawing it now is so the **folder structure on both sides of the stack matches it**. When Phase 3 ships Gmail intake, no one has to ask where it goes — `services/intake/gmail/` and `modules/intake/` are already waiting.

### 2.3 Module Map

The product has 11 first-class modules. Each one has a mobile folder and a backend service folder by the same name.

| Module | Purpose | First phase that activates it |
|---|---|---|
| `dashboard` | Personalized home; quick read of the day | Phase 1 (placeholder) → Phase 4 (real) |
| `intake` | Gmail, RSS, APIs, webhooks (the "INPUT" stage) | Phase 3 |
| `verification` | Source confidence, dedupe, cross-check | Phase 4 |
| `research` | Notes, threads, saved items | Phase 4 |
| `content` | Drafts, summaries, AI-assisted writing | Phase 5 |
| `publishing` | Send to Notion, web, social | Phase 5 |
| `automation` | Schedules, workflows, integrations (Zapier/Make) | Phase 6 |
| `notifications` | Push, in-app, email digests | Phase 6 |
| `analytics` | Usage, content performance | Phase 7 |
| `training` | Education product surface | Phase 8 |
| `settings` | Profile, preferences, integrations | Phase 2 |

**Why this exists:** every later phase activates one module. Module boundaries match team-of-one boundaries. We can pause `training` for a year without it affecting `intake`.

**Why best:** symmetry between FE and BE. Same vocabulary across the codebase.

**What it prevents:** the classic "where does this go?" question that produces 1500-line files.

**How it scales:** each module can later split into its own deployable, its own team, even its own repo if needed — the boundary is already there.

### 2.4 Phase Boundary Map

```
Phase 1 → Foundation (this doc)
Phase 2 → Auth + Users + Settings + first real DB
Phase 3 → Intake (Gmail primary, RSS + webhooks)
Phase 4 → Verify + Analyze + Research
Phase 5 → Create + Publish (Notion native, web/social indirect)
Phase 6 → Automation + Notifications
Phase 7 → Analytics
Phase 8 → Training
```

Each phase consumes only artifacts the previous phase produced. Phase 4 can't be built until Phase 3's intake produces real items. Phase 5 can't be built until Phase 4 produces verified, analyzed content.

---

## 3. System Architecture

### 3.1 Frontend Responsibilities

- Rendering — UI, navigation, animations, screens
- Local UX state — form values, modals, hovers, focus
- Server state caching — via React Query, never via Redux
- Auth session presence — knows whether a token exists, never validates it
- Offline awareness — graceful degradation when the network is down
- Telemetry — emits user events to backend, never stores them locally past a flush

Explicitly NOT responsible for:

- Business logic (verification rules, scoring, dedupe)
- Direct integration with third parties (Gmail, Notion, etc.)
- Secret handling beyond a single short-lived auth token
- Data persistence beyond a small AsyncStorage cache

### 3.2 Backend Responsibilities

- Every business rule (verification, scoring, clustering, summarization)
- Every third-party integration (Gmail, Notion, RSS, market APIs)
- All persistence and database access
- Authentication, authorization, session management
- Background jobs, scheduling, automation execution
- Webhooks (inbound and outbound)
- Auditing, structured logging, observability

Explicitly NOT responsible for:

- Pixel layout decisions (theme tokens live in shared / frontend land)
- Knowing which device is calling it (treats mobile and future web identically)

### 3.3 Shared Responsibilities

Lives in `packages/shared-types/` and `packages/design-system/`:

- API request/response types (TypeScript source → pydantic mirror)
- Enums (e.g. `SourceConfidence: 'low' | 'medium' | 'high'`)
- Error codes and shapes
- Design tokens (colors, typography, spacing, radii)

Both apps consume these. Neither owns them — they are infrastructure.

### 3.4 Communication Boundaries

- Mobile → Backend: HTTPS + JSON over a versioned REST API at `/v1/...`
- Backend → Mobile: same channel; push notifications via FCM/APNs from Phase 6
- Backend → Backend (services): in-process Python calls in Phase 1–5; an internal event bus introduced in Phase 4 (`shared/events.py` interface is stubbed now)
- Backend → Third parties: contained inside `integrations/<vendor>/`; never imported outside that folder

**Why these boundaries exist:** because every cross-boundary call is a place where the system can be misused. Drawing them explicitly turns every misuse into a code review conversation, not a production incident.

**How they scale:** the event bus interface lets us switch from in-process to Redis/SQS without touching any service code. The integration containment lets us swap Gmail for Outlook in one folder.

---

## 4. Monorepo Architecture

### 4.1 Why a monorepo at all

The product has a tight contract between two languages. The two worst outcomes a polyrepo produces — *type drift* and *non-atomic cross-cutting changes* — happen weekly on premium consumer products and cost dozens of hours each. A monorepo eliminates both by construction.

We re-evaluate this when backend engineering crosses ~10 people. Until then, monorepo wins on every axis that matters.

### 4.2 Top-Level Folder Structure

```
anant-capital/
├── apps/
│   ├── mobile/                    # Expo + React Native + TypeScript
│   └── backend/                   # FastAPI + Python 3.12
│
├── packages/
│   ├── design-system/             # Theme tokens, typography, primitives
│   ├── shared-types/              # API contract types (source of truth)
│   └── config/                    # Shared eslint, tsconfig, prettier, ruff
│
├── infra/
│   ├── docker/                    # Dockerfiles, docker-compose for local dev
│   ├── env/                       # .env.example files per environment
│   └── scripts/                   # bootstrap, lint-all, type-check-all, gen-pydantic
│
├── docs/
│   ├── PHASE_1_ARCHITECTURE.md    # this file
│   ├── design-system.md           # token reference + visual rules
│   └── adr/                       # one .md per major decision (immutable)
│
├── .github/workflows/             # CI: lint, type-check, drift-check
├── package.json                   # workspace root
├── pnpm-workspace.yaml
├── pyproject.toml                 # ruff + mypy root config
└── README.md
```

### 4.3 Package Structure

Three packages, three purposes:

- **`design-system`** — UI tokens and primitives. Imported by `apps/mobile`. Will later be imported by a web app.
- **`shared-types`** — TypeScript interfaces and enums. Imported by `apps/mobile` directly; transformed into pydantic and consumed by `apps/backend`.
- **`config`** — lint/format/typecheck config presets so every workspace inherits the same standards.

### 4.4 Shared Code Strategy

| If the code is... | It lives in... |
|---|---|
| Used only by mobile | `apps/mobile/src/` |
| Used only by backend | `apps/backend/src/anant/` |
| A type that crosses FE↔BE | `packages/shared-types/` |
| A visual primitive (Button, Card) | `packages/design-system/` |
| A tool config (eslint, mypy) | `packages/config/` |
| A bash/typescript script used only at build/CI time | `infra/scripts/` |

Rule: if you're tempted to put cross-cutting code in `apps/mobile/src/shared/`, stop. It belongs in a package.

### 4.5 Why this layout is scalable

- A new app (web, desktop, CLI) drops into `apps/` and immediately consumes the same packages
- A new package follows the existing template; no new conventions
- A new module follows the symmetric pattern on both sides of the stack
- The scripts folder centralizes all build-time logic — no scattered shell snippets

### 4.6 What it prevents

- **Drift** between FE/BE types (impossible by construction)
- **Hidden dependencies** between apps (only `packages/` is shared)
- **Convention sprawl** (one lint config, one tsconfig base, one ruff)

---

## 5. Frontend Architecture

### 5.1 Why this section exists

The mobile shell is the surface every user touches. A wrong choice here multiplies as we add screens. The decisions below intentionally favor *boring, durable* technology because the product itself will be the source of newness.

### 5.2 App Shell

- **Expo (managed workflow)** + React Native + TypeScript (strict)
- Single `App.tsx` mounts: ErrorBoundary → ReduxProvider → QueryClientProvider → ThemeProvider → NavigationContainer
- Splash + brand mark from boot to first paint

### 5.3 Folder Structure

```
apps/mobile/
├── App.tsx
├── app.json                       # Expo config
├── src/
│   ├── modules/                   # one folder per product module
│   │   ├── dashboard/
│   │   ├── intake/
│   │   ├── verification/
│   │   ├── research/
│   │   ├── content/
│   │   ├── publishing/
│   │   ├── automation/
│   │   ├── notifications/
│   │   ├── analytics/
│   │   ├── training/
│   │   └── settings/
│   │
│   │   # Each module shape:
│   │   #   <module>/
│   │   #     screens/      — top-level screens
│   │   #     components/   — module-private components
│   │   #     hooks/        — useXxxQuery, useXxxMutation
│   │   #     api/          — typed API client wrappers
│   │   #     types.ts      — re-exports from shared-types
│   │
│   ├── navigation/                # RootNavigator, tab navigator, auth navigator, deep links
│   ├── store/                     # Redux store + slices (auth, app, theme)
│   ├── providers/                 # QueryClient, Redux, Theme
│   ├── lib/
│   │   ├── api/                   # axios/fetch wrapper, interceptors, error mapping
│   │   ├── logger.ts              # console + remote sink stub
│   │   └── errors.ts              # AppError, error boundary helpers
│   └── assets/                    # fonts, icons, splash
│
└── tests/
```

### 5.4 Navigation

- **React Navigation** (`@react-navigation/native` + `native-stack` + `bottom-tabs`)
- Three navigators:
  - `AuthNavigator` — sign in, sign up, forgot password (placeholders in Phase 1)
  - `RootTabNavigator` — Home, Research, Content, Notifications, Settings
  - Module stacks — each tab pushes its own stack so deep links land precisely
- Deep link config defined once in `navigation/linking.ts`

**Why best:** React Navigation is the de-facto standard, ships native-feeling transitions, and has first-class deep linking.

**What it prevents:** the painful refactor when you bolt deep linking on after the fact.

**How it scales:** each module owns its own stack; adding screens never touches the root navigator.

### 5.5 Theme System

- All tokens live in `packages/design-system/src/tokens/`
- `ThemeProvider` exposes tokens via a typed hook `useTheme()`
- No component may use a hex value or a magic number — lint rule enforces this from Phase 1 day 1
- Dark mode is the only mode in Phase 1; a `mode` field exists in the theme for future light mode but is unused

### 5.6 Component System

Phase 1 ships exactly these primitives, in `packages/design-system/src/components/`:

- `Screen` — safe-area-aware container, applies background tokens
- `Text` — variant prop maps to typography tokens; no other font styling permitted at call sites
- `Button` — variants: `primary` (gold), `secondary` (glass), `ghost`, `danger`
- `Card` — elevated surface with subtle glass blur option
- `Divider`
- `Spacer` — pure layout, never margins-as-positioning
- `Icon` — Lucide-react-native, sized via tokens
- `Pressable` — wraps RN Pressable with haptics + scale animation
- `Skeleton` — loading placeholder

Anything richer (charts, ticker rows, news cards) is built in the phase that needs it, not now.

**Why best:** we resist the urge to build 50 components for screens that don't exist yet. Premature primitives become tomorrow's deprecated code.

### 5.7 State Management Strategy — the Three-Bucket Rule

| Bucket | Tool | What goes here |
|---|---|---|
| Server state | React Query | Anything the backend owns: items, drafts, verifications, notifications |
| Global app state | Redux Toolkit | Auth session, current user, theme preference, feature flags |
| Local UI state | useState / useReducer | Form inputs, modal open/closed, focus, hover |

Code review will reject:

- Fetched data stored in Redux
- Form input stored in Redux
- Context for frequently-updated state (Context is fine only for static values)

**Why best:** each tool is exceptional at its bucket and bad at the others. Mixing them is the most common cause of unpredictable RN apps.

**What it prevents:** cache invalidation bugs, re-render storms, the "single source of truth that's actually three sources" anti-pattern.

### 5.8 Screen Grouping

Tabs (visible in Phase 1):

- **Home** — placeholder dashboard
- **Research** — placeholder
- **Content** — placeholder
- **Notifications** — placeholder
- **Settings** — visible, links to a profile placeholder

Hidden modules (mounted in nav but not in tabs yet):

- `intake`, `verification`, `publishing`, `automation`, `analytics`, `training` — accessible by route but no tab icon. They appear in the UI as their phase activates.

---

## 6. Backend Architecture

### 6.1 Why this section exists

The backend will eventually own every meaningful business rule in the product. Phase 1 defines the seams so each later phase fills one in without disturbing the others.

### 6.2 Python Service Layout

- **Python 3.12** + **FastAPI** + **Pydantic v2**
- ASGI, async-first
- **Dependency injection** via FastAPI's `Depends()` — no custom DI framework
- **ruff** for lint + format, **mypy --strict** for types, **pytest** for tests
- **uv** for dependency management (fast, deterministic)

```
apps/backend/
├── pyproject.toml
├── src/anant/
│   ├── main.py                    # app factory, mounts routers, applies middleware
│   ├── config.py                  # Pydantic Settings; reads env, validates at boot
│   ├── core/
│   │   ├── logging.py             # structured JSON logger
│   │   ├── errors.py              # AppError base class, exception handlers
│   │   ├── middleware.py          # request ID, timing, CORS, auth (later)
│   │   ├── pagination.py          # cursor pagination helpers
│   │   └── dependencies.py        # cross-cutting deps (current_user, db session)
│   │
│   ├── services/                  # one folder per domain
│   │   ├── users/
│   │   ├── intake/
│   │   ├── verification/
│   │   ├── research/
│   │   ├── content/
│   │   ├── publishing/
│   │   ├── automation/
│   │   ├── notifications/
│   │   ├── analytics/
│   │   └── training/
│   │
│   │   # Each service shape:
│   │   #   <service>/
│   │   #     router.py        — HTTP layer ONLY
│   │   #     service.py       — business logic; no HTTP, no DB direct
│   │   #     repository.py    — storage interface (abstract in Phase 1)
│   │   #     schemas.py       — pydantic request/response models
│   │   #     models.py        — domain entities (frozen dataclasses)
│   │   #     events.py        — domain events this service emits
│   │
│   ├── integrations/              # outbound vendor clients (populated Phase 3+)
│   │   ├── gmail/
│   │   ├── notion/
│   │   ├── rss/
│   │   └── ai/
│   │
│   └── shared/
│       ├── types.py               # generated pydantic mirror of shared-types
│       └── events.py              # event bus interface (in-process now)
│
└── tests/
    ├── unit/
    └── integration/
```

### 6.3 API Boundaries

- All HTTP under `/v1/...` from day 1 (versioned)
- Each service owns one prefix: `/v1/users`, `/v1/intake`, `/v1/research`, etc.
- `GET /v1/health` and `GET /v1/version` live at the root
- OpenAPI auto-generated at `/v1/docs` (Swagger) and `/v1/redoc`
- All endpoints return JSON with a canonical envelope (see §7.2)
- Pagination is cursor-based, not offset — Phase 1 defines the contract; Phase 3 first uses it

### 6.4 Config Structure

```python
# config.py
class Settings(BaseSettings):
    environment: Literal["dev", "staging", "prod"]
    log_level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    cors_origins: list[str]
    database_url: str | None = None     # Phase 2 onwards
    gmail_client_id: str | None = None  # Phase 3 onwards
    # ...
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
```

Rules:

- Every variable is typed; no `os.environ.get(...)` anywhere else in the codebase
- Missing required vars = boot failure, never a silent default
- Secrets live in environment-specific secret managers (Phase 2 picks one); `.env.example` documents shape, never values

### 6.5 Middleware Structure

Order matters. In `main.py`:

```
RequestIDMiddleware       # generate or accept X-Request-ID
TimingMiddleware          # X-Response-Time header
CORSMiddleware            # locked to known origins
GZipMiddleware            # responses > 1KB
AuthMiddleware            # stub in Phase 1; real in Phase 2
ErrorHandlingMiddleware   # last so it wraps everything
```

**Why best:** middleware order is invisible and ruinous when wrong. Locking it in a documented order prevents the worst class of debugging sessions.

### 6.6 Logging & Error Handling

- **Structured JSON logs** (key/value), one event per line, never multi-line
- Every log record carries: `request_id`, `service`, `event`, `level`, `latency_ms`, `user_id` (when present)
- **No PII** in log values — a redaction layer scrubs `email`, `token`, `address`, `phone`, `name` fields
- All exceptions inherit from `AppError(code: str, http_status: int, message: str)`
- A global handler converts `AppError` to the canonical error envelope (see §7.3)
- Unhandled exceptions return a generic `INTERNAL_ERROR` envelope; full traceback in logs only

**What it prevents:** the most common production failure — a leaked stack trace exposing secrets or internals.

**How it scales:** structured logs flow into any log platform (Datadog, Honeycomb, Loki) without reformatting.

---

## 7. Shared Contracts

### 7.1 Type Strategy

- `packages/shared-types/` is the **source of truth** in TypeScript
- A build script (`infra/scripts/gen-pydantic.ts`) reads each file and emits matching pydantic models into `apps/backend/src/anant/shared/types.py`
- CI step compares generated output against committed file; mismatch fails the build
- Frontend imports types directly; backend imports the pydantic mirror

```
packages/shared-types/
├── src/
│   ├── common.ts        # ID, Timestamp, Cursor, Pagination, ErrorEnvelope
│   ├── users.ts
│   ├── intake.ts
│   ├── verification.ts
│   ├── research.ts
│   ├── content.ts
│   ├── publishing.ts
│   ├── automation.ts
│   ├── notifications.ts
│   ├── analytics.ts
│   ├── training.ts
│   └── index.ts
```

Phase 1 ships only `common.ts` and `users.ts` populated — others are empty stubs.

### 7.2 Response Envelope

Every successful response:

```ts
interface ApiResponse<T> {
  data: T;
  meta?: {
    pagination?: { nextCursor: string | null; prevCursor: string | null };
    requestId: string;
    serverTime: string;  // ISO 8601
  };
}
```

### 7.3 Error Envelope

Every error response — 4xx and 5xx alike — uses one shape:

```ts
interface ApiError {
  error: {
    code: string;              // machine-readable: 'AUTH_REQUIRED', 'NOT_FOUND', etc.
    message: string;           // human-readable, safe to surface
    details?: Record<string, unknown>;  // validation errors, field-level info
    requestId: string;
  };
}
```

Codes are stable; messages may change. Clients branch on `code`, never on `message`.

### 7.4 Request Schema Rules

- Every request body is a pydantic model on the backend, an interface in shared-types
- Path params are typed; no stringly-typed IDs
- Query params validated by pydantic with explicit defaults
- Optional fields are explicit — no `Partial<T>` games

### 7.5 Frontend/Backend Contract Rules

1. The contract is changed by editing `shared-types`, not by changing one side
2. Breaking changes require a new endpoint version (`/v2/...`); never silent
3. New optional fields are not breaking — clients ignore unknown fields
4. Enums are exhaustive on both sides; adding an enum value is a breaking change unless the API also returns `__future__` defaults
5. Every endpoint has a contract test that asserts the response matches the type at runtime in CI

**Why best:** the contract is the most expensive thing to break and the cheapest to keep right *if* you make it visible. Putting it in one place makes it visible.

**What it prevents:** silent FE/BE drift that ships to production and only surfaces as user reports.

---

## 8. Design System Specification

### 8.1 Why this section exists

Premium feel is not a bonus feature — it is the product's identity. A "fine but generic" admin-template look would erase the differentiation. The system below codifies the look so every screen, built by anyone, looks like it belongs.

### 8.2 Color Tokens

```ts
colors = {
  bg: {
    primary:   '#0A0A0A',       // app background
    secondary: '#121212',       // section / scroll background
    card:      '#181818',       // card base
    elevated:  '#1F1F1F',       // modals, dropdowns, sheets
  },
  text: {
    primary:   '#FFFFFF',       // headings, key numbers
    secondary: '#A0A0A0',       // labels, supporting copy
    tertiary:  '#6B6B6B',       // metadata, captions
    inverse:   '#0A0A0A',       // on gold buttons
  },
  accent: {
    gold:      '#D4AF7A',       // soft, refined — never yellow
    goldMuted: '#8C7553',
    goldGlow:  'rgba(212,175,122,0.15)',
  },
  semantic: {
    success: '#4ADE80',
    warning: '#FBBF24',
    danger:  '#F87171',
    info:    '#60A5FA',
  },
  border: {
    subtle:  'rgba(255,255,255,0.06)',
    default: 'rgba(255,255,255,0.10)',
    strong:  'rgba(255,255,255,0.18)',
  },
}
```

### 8.3 Glossy / Glass Surfaces

- Implemented via `expo-blur` BlurView wrapped in our `Card` primitive
- Reserved for **overlays only**: modals, sheets, floating headers, the search bar overlay
- Never used on dense content (kills readability)
- Glass surfaces use `bg.elevated` at 70% opacity with `intensity={40}` blur

**Why best:** restraint is the difference between premium and gaudy. Glass everywhere becomes nothing; glass on overlays becomes signature.

### 8.4 Spacing Rules

```ts
spacing = { 0:0, 1:4, 2:8, 3:12, 4:16, 5:20, 6:24, 8:32, 10:40, 12:48, 16:64 };
```

- 8pt grid; everything is a multiple of 4
- Minimum screen horizontal padding: `spacing[4]` (16)
- Section spacing: `spacing[6]` (24) minimum
- Card internal padding: `spacing[5]` (20)
- No magic numbers in components — every spacing reference goes through the token

### 8.5 Typography Rules

```ts
typography = {
  display: { size: 32, weight: '700', lineHeight: 38, letterSpacing: -0.5 },
  h1:      { size: 24, weight: '700', lineHeight: 30 },
  h2:      { size: 20, weight: '600', lineHeight: 26 },
  body:    { size: 16, weight: '400', lineHeight: 24 },
  bodySm:  { size: 14, weight: '400', lineHeight: 20 },
  caption: { size: 12, weight: '500', lineHeight: 16, letterSpacing: 0.4 },
  mono:    { size: 13, weight: '500', lineHeight: 18, fontFamily: 'JetBrainsMono' },
}
```

- **Inter** for UI text. **JetBrains Mono** for numbers, tickers, addresses, hashes
- Six sizes total. No `fontSize: 17` because someone felt like it
- Letter spacing is intentional, not decorative

### 8.6 Card Rules

- Background: `bg.card`
- Border: `border.subtle` (1px)
- Radius: `radius.lg` (14)
- Padding: `spacing[5]` (20)
- Optional `elevated` variant: bumps background to `bg.elevated`, adds subtle drop shadow
- Optional `glass` variant: applies blur (overlay use only)
- Never nest cards more than one level deep

### 8.7 Button Rules

- Primary: gold background, inverse text, full weight font
- Secondary: glass surface, primary text
- Ghost: transparent, secondary text, used in toolbars only
- Danger: danger color background, white text, used only on destructive actions
- Minimum touch target: 44pt height (Apple HIG)
- Loading state always renders the same width as resting state (no layout shift)

### 8.8 Visual Hierarchy Rules

1. One `display` per screen, max. It anchors the eye.
2. Numbers in mono; labels in body
3. Gold accent reserved for: primary CTAs, active tab indicators, confidence chips
4. Maximum 3 levels of vertical hierarchy per card (heading → body → meta)
5. Whitespace is content — leave it
6. Never use color alone to convey state; pair with icon or label

**What this prevents:** the slow drift into clutter that kills premium-feel products at month 6.

---

## 9. Navigation Map

### 9.1 Auth Flow (placeholder in Phase 1)

```
SplashScreen
  │
  ▼
AuthNavigator
  ├── SignInScreen      (placeholder — no real auth)
  ├── SignUpScreen      (placeholder)
  └── ForgotPasswordScreen (placeholder)
       │
       ▼  (on "sign in" tap, Phase 1 just navigates)
  RootTabNavigator
```

In Phase 1, "sign in" is a button that navigates straight to Home. Phase 2 replaces it with real auth.

### 9.2 Root Tab Navigator

```
RootTabNavigator (bottom tabs)
  ├── Home
  │     └── DashboardStack → DashboardScreen (placeholder)
  ├── Research
  │     └── ResearchStack → ResearchHomeScreen (placeholder)
  ├── Content
  │     └── ContentStack → ContentHomeScreen (placeholder)
  ├── Notifications
  │     └── NotificationsStack → NotificationsHomeScreen (placeholder)
  └── Settings
        └── SettingsStack
              ├── SettingsHomeScreen
              └── ProfileScreen (placeholder)
```

### 9.3 Hidden Modules (mounted, no tab)

Reachable by route name; no tab icons in Phase 1:

- `intake/*`, `verification/*`, `publishing/*`, `automation/*`, `analytics/*`, `training/*`

These are added to the visible nav as their phase ships.

### 9.4 Deep Link Map

`navigation/linking.ts` defines:

```
anantcapital://home
anantcapital://research/:id
anantcapital://content/:id
anantcapital://notifications
anantcapital://settings/profile
```

Phase 1 wires the config; Phase 3+ uses them.

**Why best:** defining deep links now means notifications and email links work from the first day Phase 6 ships.

---

## 10. Database Sketch

> No database is created in Phase 1. This section is the *contract* Phase 2 will implement. The repository interfaces in §6 are the only Phase 1 code that touches storage.

### 10.1 Users

```
users
─────────────────────────────────────────
id                uuid     pk
email             text     unique, not null
email_verified_at timestamp
password_hash     text     (auth method TBD Phase 2)
status            enum     ('active', 'suspended', 'deleted')
created_at        timestamp
updated_at        timestamp
deleted_at        timestamp nullable (soft delete)
```

**Why:** core identity. Email-keyed because that's how integrations (Gmail, Notion) match.

**What it prevents:** rewiring identity later. Adding OAuth providers in Phase 3 is a new table, not a migration here.

### 10.2 Profiles

```
profiles
─────────────────────────────────────────
user_id          uuid     pk, fk → users.id
display_name     text
avatar_url       text     nullable
role             enum     ('founder', 'analyst', 'editor', 'reader')
timezone         text     IANA
locale           text     BCP-47
bio              text     nullable
created_at       timestamp
updated_at       timestamp
```

**Why separate from users:** identity (auth) and presentation (profile) have different lifecycles and different access patterns. A profile can be fully replaced without touching auth.

### 10.3 Preferences

```
preferences
─────────────────────────────────────────
user_id              uuid    pk, fk → users.id
theme                enum    ('dark')  -- 'light' added later
notification_email   bool
notification_push    bool
notification_digest  enum    ('off', 'daily', 'weekly')
default_intake_filter jsonb  -- shape TBD Phase 3
created_at           timestamp
updated_at           timestamp
```

**Why a jsonb column for `default_intake_filter`:** intake filtering rules will evolve weekly in Phase 3. Promoting fields out of jsonb into columns is cheap; demoting is not.

### 10.4 Sessions

```
sessions
─────────────────────────────────────────
id              uuid     pk
user_id         uuid     fk → users.id
refresh_token_hash text  unique not null
device_id       text     (mobile install id)
device_label    text     ('iPhone 15 Pro')
ip_address      inet
user_agent      text
created_at      timestamp
expires_at      timestamp
revoked_at      timestamp nullable
```

**Why hash, not raw tokens:** if the DB leaks, sessions stay safe.

**Why device fields:** required for "sign out everywhere except this device" — a basic premium-product feature.

### 10.5 Index Sketch

- `users.email` unique
- `sessions.user_id` btree (lookup all sessions for a user)
- `sessions.expires_at` btree (cleanup job)
- Soft delete: every `deleted_at` indexed partial `WHERE deleted_at IS NOT NULL`

### 10.6 Why this is the right Phase 1 sketch

- Only the domain Phase 2 needs is sketched (users, profiles, preferences, sessions). Anything else is speculative
- The shapes are conservative — every column listed will exist in some form regardless of DB choice
- The choice of Postgres (assumed) is not hard-coded into the interface; a different store could fulfill the same contract

---

## 11. Implementation Plan

### 11.1 Build Order (strict, dependency-ordered)

```
1. Repo + workspace bootstrap
   - pnpm workspace, root package.json, pnpm-workspace.yaml
   - pyproject.toml + uv at root
   - .gitignore, .editorconfig
   - README skeleton

2. packages/config
   - eslint, prettier, tsconfig.base.json
   - ruff config, mypy config
   - This must exist before any app so apps inherit lint/format

3. packages/shared-types
   - Folder structure
   - common.ts (Id, Timestamp, ApiResponse, ApiError, Pagination)
   - users.ts (User, Profile, Preferences, Session)
   - Empty stubs for all other module files
   - gen-pydantic.ts script
   - CI drift check

4. packages/design-system
   - Tokens: colors, typography, spacing, radius
   - ThemeProvider + useTheme hook
   - Primitives: Screen, Text, Button, Card, Divider, Spacer, Icon, Pressable, Skeleton
   - Storybook-lite preview screen (optional in Phase 1)

5. apps/backend
   - main.py with app factory
   - config.py with Settings
   - core/logging, core/errors, core/middleware
   - GET /v1/health and /v1/version
   - All 10 service folders scaffolded with router.py + ping endpoint
   - Generated pydantic mirror imported and exposed
   - Dockerfile + docker-compose.local.yml

6. apps/mobile
   - Expo init with TypeScript
   - App.tsx provider chain
   - Theme integration
   - Redux store with auth/app/theme slices (empty)
   - React Query client
   - Navigation: AuthNavigator + RootTabNavigator + module stacks
   - All placeholder screens
   - Lib: api client, logger, error boundary
   - Deep link config

7. infra
   - scripts/bootstrap.sh (one command repo setup)
   - scripts/dev.sh (boots mobile + backend)
   - .env.example files
   - Docker compose for local stack

8. CI
   - GitHub Actions: lint, type-check, drift check, tests
   - Branch protection rules documented

9. Documentation
   - README finalized
   - docs/design-system.md with token reference
   - First ADRs (one per major decision: monorepo, FastAPI, Expo, RTK+RQ, repository pattern)
```

### 11.2 Dependency Order Justification

- `config` before everything: lint rules must apply from the first line of real code
- `shared-types` before apps: both apps will import it; missing it forces re-work
- `design-system` before mobile: mobile screens can't be built before primitives exist
- Backend before mobile: lets us run integration tests against `/v1/health` from mobile's API client wiring
- Infra and CI after apps work locally: there's nothing to CI until something compiles

### 11.3 What Should Be Coded First (top 5 commits)

1. Repo bootstrap (commit 1)
2. `packages/config` with all tooling configs (commit 2)
3. `packages/shared-types/common.ts` + generation script + CI drift check (commit 3)
4. `packages/design-system` tokens + `Screen` + `Text` + `Button` (commit 4)
5. `apps/backend` boots and serves `/v1/health` returning a typed `ApiResponse<HealthStatus>` (commit 5)

After commit 5, the contract loop is closed: a backend response is typed by the same definition the mobile app will consume. Every later commit is additive.

### 11.4 What Should Wait Until Later Phases

| Item | Phase |
|---|---|
| Real auth + token issuance | 2 |
| Concrete DB + migrations | 2 |
| Gmail OAuth + intake | 3 |
| RSS / market data / crypto adapters | 3 |
| AI client (summarization, scoring) | 4 |
| Verification rules | 4 |
| Research notes persistence | 4 |
| Content drafts + Notion sync | 5 |
| Publishing pipelines | 5 |
| Automation engine + Zapier/Make bridges | 6 |
| Notification delivery (push, email digest) | 6 |
| Analytics warehouse | 7 |
| Training product surfaces | 8 |

### 11.5 Phase 1 Exit Checklist

Before Phase 2 begins:

- [ ] All success criteria in §1.3 pass
- [ ] One ADR written per major decision in §1.5
- [ ] `docs/design-system.md` is the visual source of truth
- [ ] No `TODO` or `FIXME` in production paths (tests are fine)
- [ ] CI is green on `main`
- [ ] A new engineer onboards in under 10 minutes

---

## Appendix A — Architectural Decision Records to Write

One ADR per decision below. Each ADR follows the standard format: *Context, Decision, Consequences*.

1. `ADR-001-monorepo.md` — why monorepo with pnpm workspaces
2. `ADR-002-expo-managed.md` — Expo managed vs bare RN
3. `ADR-003-fastapi.md` — FastAPI vs Django
4. `ADR-004-state-split.md` — Redux Toolkit + React Query split
5. `ADR-005-shared-types-source-of-truth.md` — TypeScript-first contracts
6. `ADR-006-repository-pattern.md` — defer DB choice via repository interfaces
7. `ADR-007-design-tokens-only.md` — no inline colors or magic numbers

---

*This document is the Phase 1 contract. Deviations require editing this document first.*
