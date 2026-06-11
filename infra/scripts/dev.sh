#!/usr/bin/env bash
# Boot backend + mobile in parallel for local development.
# Backend logs are prefixed [be], mobile logs [mob].
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

prefix() {
  local tag="$1"
  awk -v t="[$tag]" '{ print t " " $0; fflush(); }'
}

(
  cd apps/backend && \
  uv run uvicorn anant.main:app --reload --port 8000 2>&1 | prefix be
) &
BE_PID=$!

(
  pnpm --filter @anant/mobile start 2>&1 | prefix mob
) &
MOB_PID=$!

trap 'kill $BE_PID $MOB_PID 2>/dev/null || true' EXIT
wait
