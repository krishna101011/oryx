#!/usr/bin/env bash
# Anant Capital — one-command repo setup.
# Idempotent: safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

bold() { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

bold "Checking toolchain"
command -v node >/dev/null || { echo "node missing (need >= 20.11)"; exit 1; }
command -v pnpm >/dev/null || { echo "pnpm missing — install via 'npm i -g pnpm@9'"; exit 1; }
command -v python3 >/dev/null || { echo "python3 missing (need 3.12)"; exit 1; }

bold "Installing JS workspaces"
pnpm install --frozen-lockfile || pnpm install

bold "Seeding env files (if missing)"
[ -f apps/backend/.env ] || cp infra/env/.env.example.backend apps/backend/.env
[ -f apps/mobile/.env ]  || cp infra/env/.env.example.mobile  apps/mobile/.env

bold "Installing backend (uv)"
if ! command -v uv >/dev/null; then
  # Official installer — puts uv at ~/.local/bin
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
( cd apps/backend && uv sync --extra dev )

bold "Generating pydantic mirror from shared-types"
pnpm gen:pydantic

bold "Done."
echo "Run 'pnpm backend:dev' and 'pnpm mobile:dev' (in two terminals)."
