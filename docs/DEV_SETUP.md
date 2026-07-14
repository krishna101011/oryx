# Dev environment setup (VS Code + local toolchain)

This explains the `.vscode/` workspace config added to the repo: what each
piece is, why it's set up the way it is, and the one gotcha
(`ORYX_DEV_MONOPROCESS`) that has bitten people before.

It does not cover *starting* the stack day-to-day — see the "Dev stack
startup" memory / `pnpm`/`uv` commands in `CLAUDE.md` for that. This is about
the editor and debugger.

## The real toolchain (as of this writing)

- **Python**: `apps/backend/.venv`, managed by `uv 0.11.20`, running
  **Python 3.14.3**. Note `.python-version` at the repo root pins `3.12` —
  the venv itself was built against a newer 3.14 interpreter that still
  satisfies backend's `requires-python = ">=3.12"`. Nothing to fix here, just
  don't be surprised if `python --version` and `.python-version` disagree.
- **Node**: v24.14.1
- **pnpm**: 9.0.0 (pinned via `packageManager` in the root `package.json`)
- No `ruff.toml` exists — ruff runs on its defaults (see
  `uv run ruff check src tests` in `apps/backend`).
- Formatting split: **Prettier** formats TS/JS/JSON/Markdown (config at
  `packages/config/prettier.config.cjs`, re-exported from the root
  `prettier.config.cjs`); **ESLint** only lints — its shared base
  (`packages/config/eslint.base.cjs`) extends `prettier` specifically to
  disable any formatting rules that would fight with it. Python formatting
  and linting are both handled by ruff.

## What's in `.vscode/`

Note: the repo's `.gitignore` already had `.vscode/` ignored except for
`.vscode/extensions.json` (someone set that up deliberately before this
change). That convention is kept as-is: `extensions.json` is the one file
that gets committed and shared; `settings.json`, `launch.json`, and
`tasks.json` are created for local use but stay untracked, same as before.

### `extensions.json` — recommended extensions

VS Code will prompt to install these when you open the workspace:

- **ms-python.python** + **ms-python.vscode-pylance** — Python language
  support and type-aware autocomplete/navigation for the FastAPI backend.
- **charliermarsh.ruff** — runs ruff inside the editor for both linting and
  formatting Python (format-on-save is wired to it below), so you see the
  same lint errors `uv run ruff check` would report, live.
- **dbaeumer.vscode-eslint** — runs ESLint on the TS/JS code (mobile app +
  shared packages), including the project's custom rule that blocks inline
  hex colors outside the design-system package.
- **esbenp.prettier-vscode** — formats TS/JS/JSON/Markdown on save, reading
  the project's own `prettier.config.cjs` so editor output matches CI.
- **editorconfig.editorconfig** — makes VS Code respect the repo's
  `.editorconfig` (LF line endings, 2-space indent, 4-space for Python, no
  trailing whitespace) for any file type/extension that doesn't have a
  dedicated formatter.

### `settings.json` — interpreter, format-on-save, performance excludes

- Points the Python interpreter at the **real** venv
  (`apps/backend/.venv/Scripts/python.exe`), not whatever Python happens to
  be first on `PATH`. Without this, Pylance/ruff would resolve imports
  against the wrong (or no) environment.
- Per-language format-on-save: ruff for `.py`, Prettier for
  `.ts`/`.tsx`/`.js`/`.json`/`.md`. ESLint's "fix on save" runs alongside
  Prettier on TS/JS to auto-fix lint issues (not formatting — Prettier owns
  that) on every save.
- `files.exclude` / `search.exclude` / `files.watcherExclude` keep
  `node_modules`, `.venv`, `dist`, `build`, `.expo`, `__pycache__`, and lock
  files out of VS Code's search index and file watcher. This is a real
  performance win, not just tidiness — a pnpm monorepo's `node_modules` tree
  alone is tens of thousands of files, and an unfiltered watcher chews CPU
  and can miss actual file-change events under load.

### `launch.json` — debugger configs

- **"Backend: uvicorn (debug)"** — launches `uvicorn oryx.main:app --reload`
  through `debugpy`, using the real venv interpreter and loading
  `apps/backend/.env` for environment variables (`subProcess: true` so
  breakpoints still work in the reloaded worker process, not just uvicorn's
  parent process).
- **"Mobile: Expo web"** — runs `npx expo start --web` from `apps/mobile` in
  a debug-attached terminal.

### `tasks.json` — one-click commands

Run via **Terminal → Run Task…** (or `Ctrl+Shift+P` → "Run Task"):

| Task | Command | Notes |
|---|---|---|
| Backend: start (uvicorn --reload) | `uv run python -m uvicorn oryx.main:app --port 8000 --reload` | Background task; `--reload` is required (see gotcha below) |
| Mobile: start (Expo web) | `npx expo start --web` | Background task |
| Backend: run tests (pytest) | `uv run python -m pytest -q` | Default test task (`Ctrl+Shift+P` → "Run Test Task") |
| Frontend: run tests | `pnpm test` | Runs all frontend/package test scripts in parallel |
| Backend: run migrations | `uv run python -m alembic upgrade head` | Requires Postgres already running |

None of these start PostgreSQL — it's installed via Scoop as a standalone
binary, not a VS Code task, and is out of scope for this workspace config.
Start it manually first (see the dev-stack-startup notes) before running the
backend task or migrations.

## The `ORYX_DEV_MONOPROCESS` gotcha, plainly

In dev, ORYX's background workers (scheduler, drainer, calendar scheduler)
can either run as their own standalone processes, or be pulled into the
same process as the API server ("colocated") so you only have one thing to
start. That colocation is controlled by one setting:
`settings.oryx_dev_monoprocess`, read from the `ORYX_DEV_MONOPROCESS`
environment variable.

Here's the trap: this project went through an `anant` → `oryx` rename, and
this variable used to be called `ANANT_DEV_MONOPROCESS`. Pydantic settings
silently ignores environment variables it doesn't recognize — it doesn't
error, doesn't warn, it just falls back to the field's default (which is
"off"). So if you (or an old `.env`, or a copy-pasted script) still has
`ANANT_DEV_MONOPROCESS=1` sitting around, the app starts up looking totally
normal, workers just... don't run. No log line tells you why, because from
the app's point of view, nothing is wrong — it's just running with
monoprocess off, same as if you'd never asked for it.

The real `apps/backend/.env` in this repo has the correct
`ORYX_DEV_MONOPROCESS=1` line today. The `launch.json` "Backend: uvicorn
(debug)" config sets it a second time, explicitly, as a safety net — so
even if `.env` ever drifts again, the debugger session still colocates the
workers and you're not left debugging "why don't my workers start" instead
of your actual feature.

If you ever *do* hit workers silently not starting: check the exact
variable name in `apps/backend/.env` character-for-character, don't assume
it's right because it "looks" right.
