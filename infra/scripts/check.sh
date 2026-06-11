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

echo "→ backend lint + type-check (CI py-job parity)"
( cd apps/backend && uv run ruff check src tests && pnpm run type-check )

echo "→ backend tests"
( cd apps/backend && uv run pytest )

echo "✓ all checks passed"
