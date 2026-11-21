# ORYX

**Financial intelligence, from information to insight.**

```text
INPUT  →  VERIFY  →  ANALYZE  →  CREATE  →  PUBLISH
```

ORYX is a financial-intelligence platform built to turn fragmented information into structured research and useful content. It brings information intake, source and claim verification, research workflows, AI-assisted content creation, publishing, automation, analytics, and team workspaces into one product.

> **Project status:** ORYX is an actively developed product, not a finished production service. The repository contains working application areas alongside foundations, staged features, provider integrations that require configuration, and work still in progress. A module being present in the codebase does not mean every workflow is production-ready or enabled by default.

---

## Product overview

The product is organized around a research-to-publication workflow:

1. **Input** — collect information from supported sources and normalize it for downstream work.
2. **Verify** — extract claims, connect evidence, assess source credibility, and surface conflicts for review.
3. **Analyze** — organize verified information into research objects and workspaces.
4. **Create** — turn research into drafts and other content with AI-assisted workflows.
5. **Publish** — configure destinations and deliver or export approved content.

The repository also contains supporting product areas for accounts and workspaces, automation and activity, analytics, billing foundations, and learning through ORYX Academy.

### Current implementation notes

- The backend exposes service areas for authentication, accounts, workspaces, intake, verification, claims and evidence, research, content drafts, publishing, automation, analytics, training, billing, and related platform functions.
- ORYX Academy has an implemented course and lesson workflow, including course discovery, enrollment, progress, and lesson navigation.
- Publishing and external-provider workflows depend on credentials and provider configuration. Several delivery integrations default to non-delivering or log-only modes until configured.
- The Markets work is at a foundation / development stage. Do not assume a complete live-market terminal or live market-data feed is available merely because chart-related code and foundations exist.
- Feature flags and environment settings affect which capabilities are active.

---

## Technology stack

| Area | Technologies |
|---|---|
| Mobile application | React Native, Expo, TypeScript |
| Web experience | React Native Web |
| Backend API | Python, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy, asyncpg |
| Database migrations | Alembic |
| Frontend state and data | Redux Toolkit, TanStack Query |
| Shared API contracts | TypeScript shared-types with generated Pydantic mirrors |
| Monorepo | pnpm workspaces; Python dependencies managed with uv |
| Charts | TradingView Lightweight Charts integration |
| Quality checks | ESLint, Prettier, Ruff, mypy, pytest, TypeScript checks |

---

## Repository structure

```text
oryx/
├── apps/
│   ├── mobile/                 React Native + Expo application
│   └── backend/                FastAPI backend
├── packages/
│   ├── design-system/          Shared design tokens and UI primitives
│   ├── shared-types/           Shared TypeScript API contracts
│   └── config/                 Shared development configuration
├── infra/
│   ├── env/                    Environment templates
│   └── scripts/                Bootstrap, development, and check scripts
├── docs/                       Architecture, setup, security, and ADRs
├── .github/                    GitHub workflows
├── package.json                Root scripts and toolchain settings
├── pnpm-workspace.yaml         JavaScript workspace definition
└── pyproject.toml              Root Python tooling configuration
```

---

## Getting started

### Prerequisites

- Node.js **20.11 or newer**
- pnpm **9 or newer**
- Python **3.12 or newer**
- PostgreSQL
- `uv` (the bootstrap script installs it if it is not available)
- Expo Go on a device, or an iOS / Android simulator, if you want to run the mobile app

### 1. Clone the repository

```bash
git clone https://github.com/Krishna101011/oryx.git
cd oryx
```

### 2. Bootstrap the project

```bash
./infra/scripts/bootstrap.sh
```

The bootstrap script installs the JavaScript workspaces, prepares the Python backend environment, creates local environment files when they are missing, and generates the Pydantic mirror from the shared TypeScript contracts.

**Important:** bootstrap does not install or start PostgreSQL and does not apply database migrations. Make sure PostgreSQL is running and that the database configured in `apps/backend/.env` exists before starting database-backed workflows.

### 3. Configure the backend

The backend reads its local settings from `apps/backend/.env`. The example configuration uses this local PostgreSQL URL by default:

```text
postgresql+asyncpg://anant:anant@localhost:5432/anant
```

Change it to match your local PostgreSQL user, password, host, port, and database. Review the environment template and backend settings before enabling integrations.

Some capabilities need additional configuration. Examples include:

- `JWT_SECRET`: replace the development placeholder outside local development.
- `INTAKE_KMS_KEY`: required when using encrypted intake credentials.
- `ORYX_PUBLISH_KEY`: required when using encrypted publishing-target credentials.
- `ANTHROPIC_API_KEY`: required when using the Anthropic AI provider.
- `AI_PROVIDER`: supports `anthropic`, `ollama`, and `openai_compatible`; the latter two need their corresponding local or vendor settings.
- Gmail OAuth, payment, email, push, and publishing providers each require their own credentials and configuration when enabled.

Never commit real secrets or production credentials.

### 4. Apply database migrations

With PostgreSQL running and `DATABASE_URL` correctly configured:

```bash
cd apps/backend
uv run python -m alembic upgrade head
cd ../..
```

### 5. Run the backend and mobile app

Use two terminals from the repository root:

**Terminal 1:**

```bash
pnpm backend:dev
```

The FastAPI backend starts on `http://localhost:8000`. The health endpoint is:

```text
http://localhost:8000/v1/health
```

The interactive API documentation is:

```text
http://localhost:8000/v1/docs
```

**Terminal 2:**

```bash
pnpm mobile:dev
```

Expo starts the mobile development server. Follow its terminal instructions to open the app on a device or simulator.

You can also use the helper script to start both development processes:

```bash
./infra/scripts/dev.sh
```

---

## Development commands

Run these from the repository root unless stated otherwise.

| Command | Purpose |
|---|---|
| `pnpm lint` | Lint JavaScript / TypeScript workspaces |
| `pnpm type-check` | Run TypeScript checks across configured workspaces |
| `pnpm test` | Run configured JavaScript workspace tests |
| `pnpm gen:pydantic` | Regenerate Pydantic models from shared TypeScript contracts |
| `pnpm drift:check` | Check that generated contracts are synchronized |
| `./infra/scripts/check.sh` | Run the repository's local quality-check sequence |
| `pnpm backend:dev` | Start the FastAPI development server |
| `pnpm mobile:dev` | Start the Expo development server |

Backend checks can be run from `apps/backend`:

```bash
uv run python -m pytest -q
uv run ruff check src tests
```

The backend test suite may require a reachable database for integration tests. Consult the test configuration and documentation before assuming the full suite can run against an empty local environment.

### Shared API contract workflow

The shared TypeScript contracts in `packages/shared-types/` are the source of truth for generated backend Pydantic models.

When changing an API contract:

1. Edit the relevant source under `packages/shared-types/`.
2. Run `pnpm gen:pydantic`.
3. Include both the source contract and generated backend mirror in the same change.
4. Run `pnpm drift:check` to verify synchronization.

---

## Architecture and project documentation

Start with these files when exploring the project:

- [`CLAUDE.md`](CLAUDE.md) — repository-level development guidance and project conventions.
- [`docs/DEV_SETUP.md`](docs/DEV_SETUP.md) — local development environment and editor setup.
- [`docs/adr/INDEX.md`](docs/adr/INDEX.md) — Architecture Decision Records and the reasoning behind technical decisions.
- [`docs/SECURITY.md`](docs/SECURITY.md) — security implementation notes, test coverage, and operator responsibilities.
- [`infra/env/`](infra/env/) — example environment configuration.

Some older phase documents describe earlier snapshots of the product. When documentation conflicts with the current implementation, verify behavior against the current source code, tests, migrations, and configuration rather than assuming an older phase document is authoritative.

---

## Security considerations

The codebase includes security-related implementation such as password hashing, signed access tokens, refresh-token rotation and reuse detection, workspace authorization checks, credential-encryption paths, request controls, audit events, and sensitive-field log redaction.

This is not a guarantee that a deployment is secure by default. Operators must configure production secrets, database access, HTTPS termination, backups, provider credentials, rate limiting appropriate to the deployment topology, and monitoring. In particular, never use the development JWT secret or example encryption values in staging or production.

See [`docs/SECURITY.md`](docs/SECURITY.md) for implementation details and explicit operational responsibilities.

---

## Contributing and project status

ORYX is under active development. Before changing a subsystem:

1. Read the relevant architecture notes and ADRs.
2. Inspect the current implementation and tests.
3. Check feature flags and provider defaults.
4. Preserve shared contract generation and migration discipline.
5. Run the applicable checks before proposing a change.

The repository's architecture and implementation continue to evolve. Treat this README as a product and developer entry point, not as a substitute for the detailed technical documentation.

---

## License

**Proprietary — ORYX. All rights reserved.**

No open-source license is included in this repository. Public visibility on GitHub does not by itself grant permission to reuse, modify, or redistribute the code.
