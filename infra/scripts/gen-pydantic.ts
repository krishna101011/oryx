#!/usr/bin/env tsx
/**
 * gen-pydantic.ts — Verifies the pydantic mirror of packages/shared-types/src/.
 *
 * Phase 1 emitted the Python file from an inlined template literal.
 * Phase 2: the type catalog outgrew that approach. The pydantic file is now
 * maintained as a *committed mirror* at the target path. This script verifies
 * (a) every TS source exists and (b) the target parses as Python.
 *
 * Convention enforced by the PR template:
 *   Any change to packages/shared-types/src/* must include a matching change
 *   to apps/backend/src/anant/shared/types.py in the same PR.
 *
 * Flags:
 *   --check   exit non-zero if target is missing or unparseable (CI uses this)
 */
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..', '..');
const TARGET = resolve(REPO_ROOT, 'apps/backend/src/anant/shared/types.py');

const SOURCES = [
  'common.ts', 'accounts.ts', 'profiles.ts', 'workspaces.ts', 'preferences.ts',
  'sources.ts', 'sessions.ts', 'auth.ts', 'activity.ts', 'alerts.ts',
  'feature-flags.ts', 'onboarding.ts', 'users.ts',
  'intake.ts', 'verification.ts', 'research.ts', 'content.ts',
  'publishing.ts', 'automation.ts', 'analytics.ts', 'training.ts',
];

function main(): void {
  for (const src of SOURCES) {
    const p = resolve(REPO_ROOT, 'packages/shared-types/src', src);
    if (!existsSync(p)) {
      console.error(`Missing shared-types source: ${p}`);
      process.exit(1);
    }
  }
  if (!existsSync(TARGET)) {
    console.error(`Pydantic mirror missing: ${TARGET}`);
    process.exit(1);
  }
  // Forward slashes keep the embedded literal valid on Windows; python3 is
  // POSIX-only, so fall back to python.
  const target = TARGET.replace(/\\/g, '/');
  const probe = `-c "import ast; ast.parse(open('${target}', encoding='utf-8').read())"`;
  try {
    execSync(`python3 ${probe}`, { stdio: 'pipe' });
  } catch {
    try {
      execSync(`python ${probe}`, { stdio: 'pipe' });
    } catch (e) {
      console.error(`Pydantic mirror does not parse: ${e}`);
      process.exit(1);
    }
  }
  console.warn('shared-types pydantic mirror present and parses.');
}

main();
