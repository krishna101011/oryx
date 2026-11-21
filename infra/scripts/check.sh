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

if [[ -z "${ORYX_TEST_DB:-}" ]]; then
  echo "ERROR: ORYX_TEST_DB is required for the full CI-equivalent check." >&2
  echo "Start a disposable PostgreSQL database and set ORYX_TEST_DB first." >&2
  exit 1
fi

# Keep migrations and tests pointed at the same disposable database.
export DATABASE_URL="$ORYX_TEST_DB"

echo "→ apply database migrations"
( cd apps/backend && uv run --no-sync alembic upgrade head )

echo "→ backend tests (unit + PostgreSQL integration)"
# `python -m pytest` avoids a known intermittent uv/pytest launcher issue
# on this Windows Git Bash setup. The CI workflow uses the standard launcher.
( cd apps/backend && uv run --no-sync python -m pytest -q )

echo "✓ all checks passed"
