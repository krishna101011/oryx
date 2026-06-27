#!/usr/bin/env bash
# Run every check CI runs, locally.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "→ shared-types drift check"
pnpm drift:check

echo "→ lint (parallel)"
pnpm lint

echo "→ type-check (parallel)"
pnpm type-check

# `uv run` without --no-sync exact-syncs the env WITHOUT dev extras —
# uninstalling pytest/ruff/mypy right before invoking them. Sync once with
# the extras, then run everything against that env.
echo "→ backend sync (locked, dev extras)"
( cd apps/backend && uv sync --extra dev )

echo "→ backend lint + type-check (CI py-job parity)"
( cd apps/backend && uv run --no-sync ruff check src tests && pnpm run type-check )

echo "→ backend tests"
# `python -m pytest` (not bare `uv run pytest`): under Git Bash on this Windows
# setup, `uv run pytest`/`uv run mypy` intermittently emit no output and exit 1
# spuriously; invoking via the module runs reliably. CI (ci.yml) is unaffected.
( cd apps/backend && uv run --no-sync python -m pytest )

echo "✓ all checks passed"
