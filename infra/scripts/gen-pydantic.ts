#!/usr/bin/env tsx
/**
 * gen-pydantic.ts — Verifies the pydantic mirror of packages/shared-types/src/.
 *
 * Phase 1 emitted the Python file from an inlined template literal.
 * Phase 2: the type catalog outgrew that approach. The pydantic file is now
 * maintained as a *committed mirror* at the target path. This script verifies:
 *   (a) every TS source exists AND the SOURCES list covers the whole directory,
 *   (b) the target parses as Python,
 *   (c) every exported string-literal union in the TS sources has a Python
 *       Literal alias of the SAME NAME whose member set is IDENTICAL.
 *
 * Convention enforced by the PR template:
 *   Any change to packages/shared-types/src/* must include a matching change
 *   to apps/backend/src/oryx/shared/types.py in the same PR.
 *
 * Matching approach for (c): a TS alias `export type Foo = 'a' | 'b';` is
 * matched to a Python top-level `Foo = Literal["a", "b"]` by identical alias
 * name. Aliases whose right-hand side is not purely string literals (e.g.
 * `Id = string`, `FlagSet = Record<...>`) are skipped. Python-only Literal
 * aliases are reported as a non-fatal notice (they may mirror inline TS
 * unions, e.g. IntakeProviderName).
 *
 * Flags:
 *   --check       exit non-zero on any failure (CI uses this)
 *   --self-test   run only the embedded mismatch fixtures and exit
 *                 (the self-test also runs automatically before every check)
 */
import { execSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..', '..');
const SRC_DIR = resolve(REPO_ROOT, 'packages/shared-types/src');
const TARGET = resolve(REPO_ROOT, 'apps/backend/src/oryx/shared/types.py');

const SOURCES = [
  'common.ts', 'accounts.ts', 'profiles.ts', 'workspaces.ts', 'preferences.ts',
  'sources.ts', 'sessions.ts', 'auth.ts', 'activity.ts', 'alerts.ts',
  'feature-flags.ts', 'onboarding.ts', 'users.ts',
  'intake.ts', 'intake-sources.ts', 'intake-events.ts', 'intake-webhooks.ts',
  'verification.ts', 'claims.ts', 'evidence.ts', 'scoring.ts', 'conflicts.ts',
  'intelligence.ts', 'research.ts', 'drafts.ts',
  'content.ts', 'publishing.ts', 'automation.ts', 'analytics.ts', 'training.ts',
  'templates.ts', 'review.ts', 'calendar.ts',
];

// index.ts is a barrel re-export; it declares no types of its own.
const NON_MIRRORED = new Set(['index.ts']);

// ---------------------------------------------------------------------------
// Semantic union diff (pure functions so the self-test can exercise them)
// ---------------------------------------------------------------------------

/** Extract `export type Name = 'a' | 'b';` aliases whose RHS is purely
 *  string literals. Returns name -> member set. */
export function extractTsUnions(source: string): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  const aliasRe = /^export type (\w+)\s*=\s*([\s\S]*?);/gm;
  for (const m of source.matchAll(aliasRe)) {
    const [, name, rawRhs] = m;
    const rhs = rawRhs.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
    const parts = rhs.split('|').map((p) => p.trim()).filter((p) => p.length > 0);
    if (parts.length === 0) continue;
    const members: string[] = [];
    let pure = true;
    for (const part of parts) {
      const lit = /^'([^']*)'$/.exec(part) ?? /^"([^"]*)"$/.exec(part);
      if (!lit) { pure = false; break; }
      members.push(lit[1]);
    }
    if (pure) out.set(name, new Set(members));
  }
  return out;
}

/** Extract top-level `Name = Literal["a", "b"]` aliases (single- or
 *  multi-line). Returns name -> member set. */
export function extractPyLiterals(source: string): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  const litRe = /^(\w+)\s*=\s*Literal\[([\s\S]*?)\]/gm;
  for (const m of source.matchAll(litRe)) {
    const [, name, body] = m;
    const members = [...body.matchAll(/"([^"]*)"/g)].map((s) => s[1]);
    out.set(name, new Set(members));
  }
  return out;
}

interface UnionDiff {
  name: string;
  missingPyAlias: boolean;
  onlyInTs: string[];
  onlyInPy: string[];
}

/** Compare TS unions to Python Literals by identical alias name. */
export function diffUnions(
  ts: Map<string, Set<string>>,
  py: Map<string, Set<string>>,
): UnionDiff[] {
  const diffs: UnionDiff[] = [];
  for (const [name, tsSet] of ts) {
    const pySet = py.get(name);
    if (!pySet) {
      diffs.push({ name, missingPyAlias: true, onlyInTs: [...tsSet].sort(), onlyInPy: [] });
      continue;
    }
    const onlyInTs = [...tsSet].filter((v) => !pySet.has(v)).sort();
    const onlyInPy = [...pySet].filter((v) => !tsSet.has(v)).sort();
    if (onlyInTs.length > 0 || onlyInPy.length > 0) {
      diffs.push({ name, missingPyAlias: false, onlyInTs, onlyInPy });
    }
  }
  return diffs;
}

function formatDiff(d: UnionDiff): string {
  if (d.missingPyAlias) {
    return `  ${d.name}: no Python Literal alias of this name ` +
      `(TS members: ${d.onlyInTs.map((v) => `'${v}'`).join(', ')})`;
  }
  const bits: string[] = [];
  if (d.onlyInTs.length > 0) {
    bits.push(`in TS but not Python: ${d.onlyInTs.map((v) => `'${v}'`).join(', ')}`);
  }
  if (d.onlyInPy.length > 0) {
    bits.push(`in Python but not TS: ${d.onlyInPy.map((v) => `'${v}'`).join(', ')}`);
  }
  return `  ${d.name}: ${bits.join('; ')}`;
}

// ---------------------------------------------------------------------------
// Self-test: prove the diff actually catches mismatches before trusting it
// ---------------------------------------------------------------------------

function selfTest(): void {
  const tsFixture = `
export type Health = 'healthy' | 'degraded' | 'disabled';
export type Kind =
  | 'gmail'
  | 'rss'; // trailing comment
export type Id = string;
`;
  // Python fixture drifts two ways: Health lacks 'disabled' and has a
  // renamed extra 'offline'; Kind matches; Orphan has no TS counterpart.
  const pyFixture = `
Health = Literal["healthy", "degraded", "offline"]
Kind = Literal[
    "gmail", "rss",
]
Orphan = Literal["x"]
`;
  const ts = extractTsUnions(tsFixture);
  const py = extractPyLiterals(pyFixture);
  const fail = (msg: string): never => {
    console.error(`SELF-TEST FAILED: ${msg}`);
    process.exit(1);
  };
  if (ts.size !== 2) fail(`expected 2 TS unions (Id skipped), got ${ts.size}`);
  if (py.size !== 3) fail(`expected 3 Python Literals, got ${py.size}`);
  const diffs = diffUnions(ts, py);
  if (diffs.length !== 1) fail(`expected exactly 1 mismatch, got ${diffs.length}`);
  const d = diffs[0];
  if (d.name !== 'Health') fail(`expected mismatch on Health, got ${d.name}`);
  if (d.onlyInTs.join(',') !== 'disabled') fail(`expected 'disabled' only-in-TS, got [${d.onlyInTs}]`);
  if (d.onlyInPy.join(',') !== 'offline') fail(`expected 'offline' only-in-Python, got [${d.onlyInPy}]`);
  // Missing-alias detection: drop Health from the Python side entirely.
  const pyWithout = new Map(py);
  pyWithout.delete('Health');
  const missing = diffUnions(ts, pyWithout);
  if (!missing.some((x) => x.name === 'Health' && x.missingPyAlias)) {
    fail('expected missing-Python-alias detection for Health');
  }
  // Clean case: identical sets on both sides must produce zero diffs.
  const clean = diffUnions(ts, extractPyLiterals(
    'Health = Literal["healthy", "degraded", "disabled"]\nKind = Literal["gmail", "rss"]',
  ));
  if (clean.length !== 0) fail(`expected clean fixture to pass, got ${clean.length} diffs`);
  console.warn('semantic-diff self-test passed (mismatch, missing-alias, and clean fixtures).');
}

// ---------------------------------------------------------------------------

function main(): void {
  selfTest();
  if (process.argv.includes('--self-test')) return;

  // (a) every listed source exists…
  for (const src of SOURCES) {
    const p = resolve(SRC_DIR, src);
    if (!existsSync(p)) {
      console.error(`Missing shared-types source: ${p}`);
      process.exit(1);
    }
  }
  // …and the list covers the whole directory, so a new module can't silently
  // ship without mirror coverage (the pre-Phase-7 gap: 5 files were unlisted).
  const listed = new Set(SOURCES);
  const unlisted = readdirSync(SRC_DIR)
    .filter((f) => f.endsWith('.ts') && !listed.has(f) && !NON_MIRRORED.has(f));
  if (unlisted.length > 0) {
    console.error(
      `shared-types files missing from gen-pydantic SOURCES: ${unlisted.join(', ')}\n` +
      'Add them to SOURCES (and mirror their types in types.py).',
    );
    process.exit(1);
  }

  // (b) the Python mirror exists and parses.
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

  // (c) semantic union diff.
  const tsUnions = new Map<string, Set<string>>();
  const tsHome = new Map<string, string>();
  for (const src of SOURCES) {
    const fileUnions = extractTsUnions(readFileSync(resolve(SRC_DIR, src), 'utf-8'));
    for (const [name, members] of fileUnions) {
      if (tsUnions.has(name)) {
        console.error(
          `Duplicate exported union alias '${name}' in ${src} and ${tsHome.get(name)}`,
        );
        process.exit(1);
      }
      tsUnions.set(name, members);
      tsHome.set(name, src);
    }
  }
  const pyLiterals = extractPyLiterals(readFileSync(TARGET, 'utf-8'));
  const diffs = diffUnions(tsUnions, pyLiterals);
  if (diffs.length > 0) {
    console.error('Semantic drift between shared-types unions and Python Literals:');
    for (const d of diffs) console.error(formatDiff(d));
    process.exit(1);
  }
  const pyOnly = [...pyLiterals.keys()].filter((n) => !tsUnions.has(n));
  if (pyOnly.length > 0) {
    console.warn(`note: Python-only Literal aliases (no exported TS alias): ${pyOnly.join(', ')}`);
  }

  console.warn(
    `shared-types pydantic mirror present, parses, and ${tsUnions.size} ` +
    'string-literal unions match their Python Literals exactly.',
  );
}

main();
