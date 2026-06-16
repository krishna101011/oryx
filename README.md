# ORYX

Premium financial intelligence platform.

```
INPUT  →  VERIFY  →  ANALYZE  →  CREATE  →  PUBLISH
```

This repository contains the **Phase 1 foundation**: monorepo skeleton, React Native (Expo) shell, FastAPI backend skeleton, shared types contract, and design system. No real features ship until Phase 2+.

---

## Prerequisites

- Node 20.11+
- pnpm 9+
- Python 3.12+
- `uv` (installed automatically by bootstrap)
- For mobile: Expo Go on a device, or an iOS / Android simulator

## Quick start

```bash
./infra/scripts/bootstrap.sh        # install everything, seed .env files
./infra/scripts/dev.sh              # boot backend + mobile in parallel
```

> **First-time lockfile:** the very first `pnpm install` creates `pnpm-lock.yaml`. Commit it. CI uses `--frozen-lockfile` and will fail until it exists.

Or run them separately:

```bash
pnpm backend:dev                    # FastAPI on :8000
pnpm mobile:dev                     # Expo dev server
```

Verify the backend:

```bash
curl http://localhost:8000/v1/health
```

OpenAPI docs: <http://localhost:8000/v1/docs>

## Repository layout

```
oryx/
├── apps/
│   ├── mobile/                 React Native (Expo) + TypeScript shell
│   └── backend/                FastAPI service-oriented skeleton
│
├── packages/
│   ├── design-system/          Tokens + primitives (single source of UI truth)
│   ├── shared-types/           TS interfaces — pydantic mirror is generated
│   └── config/                 eslint, prettier, tsconfig base, ruff, mypy
│
├── infra/
│   ├── env/                    .env templates
│   └── scripts/                bootstrap.sh, dev.sh, check.sh, gen-pydantic.ts
│
├── docs/
│   ├── PHASE_1_ARCHITECTURE.md
│   ├── PHASE_2_ARCHITECTURE.md (frozen)
│   └── adr/                    Architecture Decision Records (immutable)
│
└── .github/workflows/ci.yml
```

## Daily commands

| Command | What it does |
|---|---|
| `pnpm backend:dev` | FastAPI with reload on :8000 |
| `pnpm mobile:dev` | Expo dev server |
| `pnpm lint` | ESLint across JS workspaces (Python via `ruff` in backend) |
| `pnpm type-check` | tsc across JS workspaces (Python via `mypy --strict`) |
| `pnpm gen:pydantic` | Regenerate backend pydantic mirror from shared-types |
| `pnpm drift:check` | Fail if the mirror is out of sync (CI uses this) |
| `./infra/scripts/check.sh` | Run every check CI runs, locally |

## The contract loop

`packages/shared-types/src/` is the single source of truth for API contracts. The TypeScript interfaces there are transformed into pydantic models at `apps/backend/src/anant/shared/types.py` by `pnpm gen:pydantic`. CI rejects any commit where the mirror is stale.

When you change a contract:

1. Edit the file under `packages/shared-types/src/`
2. Run `pnpm gen:pydantic`
3. Commit both files in the same PR

## Phase discipline

This codebase ships in **strict phases**. Phase 1 is foundation only — no auth, no DB, no integrations. The frozen Phase 2 spec lives at `docs/PHASE_2_ARCHITECTURE.md`. PRs that cross phase lines are rejected at review.

See `docs/adr/` for the *why* behind every architectural choice.

## License

Proprietary — ORYX. All rights reserved.
