# ORYX — Project Memory

ORYX is a premium financial-intelligence platform (FastAPI backend + Expo/React
Native mobile + shared TypeScript types in a pnpm monorepo). It is built in
phases, each delivered as a sequence of self-contained "waves" that ship behind
feature flags. Quality bar is high: every wave ends green on type-check, lint,
drift, and the full test suite.

## Role Split (never violate this)

Claude Chat (claude.ai): architecture, freeze review, and prompt writing only.
Claude Code (this tool): all implementation — code, migrations, tests, commits.

## Where Deep Knowledge Lives

- `.claude/skills/oryx-architect/SKILL.md` — conventions, brand, naming, design
  philosophy, and the "Operational Reality" gotchas log.
- `docs/PHASE_5_ARCHITECTURE.md` (and `PHASE_1/2/3_ARCHITECTURE.md`) — frozen
  architecture. (No standalone Phase 4 doc exists; Phase 4 is covered inline.)
- `docs/adr/INDEX.md` — all architecture decision records.
- Auto-memory: `~/.claude/projects/<project>/memory/MEMORY.md` is loaded every
  session; its linked files capture recurring operational facts.

## Build & Test (the commands actually used each session)

From repo root (frontend + shared types):
- `pnpm type-check` — tsc across mobile + packages
- `pnpm lint` — eslint across mobile + packages
- `pnpm drift:check` — verify the shared-types ↔ pydantic mirror

From `apps/backend` (Python, via uv):
- `uv run python -m pytest -q` — full backend suite
- `uv run ruff check src tests` — backend lint
- `uv run python -m alembic upgrade head` — apply migrations
- DB-bound (`requires_db`) tests need a real Postgres test DB — see
  `memory/backend_integration_test_db.md` (the `anant` role lacks CREATEDB).

## Standing Instruction for Every Future Wave

At the end of any wave's completion report, include a section listing any new or
updated memory/skill files by path with a one-line purpose for each. When you
discover a genuinely reusable operational fact during a wave (a real gotcha, not
a one-off detail) — add it to `.claude/skills/oryx-architect/SKILL.md`'s
"Operational Reality" section rather than letting it live only in that wave's
report. Keep this CLAUDE.md itself small; deep additions go in the skill file,
not here.
