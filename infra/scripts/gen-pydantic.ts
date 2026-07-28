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
 *       Literal alias of the SAME NAME whose member set is IDENTICAL,
 *   (d) every exported TS interface's field set matches its same-named Python
 *       class's field set (presence, plus a bounded scalar-type check),
 *   (e) every exported TS interface/type and every Python class in the mirror
 *       has at least one REAL reference outside the mirror itself (mobile,
 *       backend, tests) — directly, or transitively via composition from
 *       something that does.
 *
 * (e) is the one that would have caught the ChatMessagesListResponse
 * incident: a type declared identically on both sides (so (c)/(d) saw no
 * drift at all) but wired into nothing real — the router returned a
 * different shape than the dead type described. (d) alone cannot catch that
 * class of bug; only (e) can. See docs/adr or the wave's completion report
 * for the incident writeup.
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
 * Matching approach for (d): TS `export interface Foo { ... }` is matched to
 * Python `class Foo(_Base): ...` by identical name, resolving `extends`/base
 * classes so inherited fields are included on both sides. Python field keys
 * are `Field(alias=...)` when present, else the raw field name. Type
 * comparison is deliberately bounded: only fields whose type reduces to a
 * bare identifier (optionally array-wrapped) on BOTH sides are compared, via
 * a small scalar-equivalence table (string<->str, Id/Timestamp/Cursor<->
 * str/datetime, number<->int/float, boolean<->bool) plus exact-name matching
 * for custom types. Unions, inline object types, and generic containers
 * (Record/dict) are skipped rather than guessed at — this codebase's own
 * nullable-but-required convention (`X | null` in TS paired with
 * `X | None = Field(default=None, ...)` in Python) would otherwise produce
 * constant false positives on optionality; see the self-test fixtures for
 * the exact patterns this intentionally does not flag.
 *
 * Matching approach for (e): build a reference graph — edges from a TS
 * interface/Python class to every other known name that appears in its own
 * field types or base/extends list. Seed "used" with every name that appears
 * (as a whole word) in apps/mobile/src, apps/backend/src (excluding this
 * mirror file itself), or apps/backend/tests. Take the closure over the
 * graph from those seeds. Anything left over is unused. KNOWN_UNWIRED is a
 * small, commented allowlist for names that are deliberately declared ahead
 * of real wiring (documented in their own file already) — everything else
 * must be either referenced or removed.
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
import ts from 'typescript';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..', '..');
const SRC_DIR = resolve(REPO_ROOT, 'packages/shared-types/src');
const TARGET = resolve(REPO_ROOT, 'apps/backend/src/oryx/shared/types.py');
const AST_FIELDS_SCRIPT = resolve(__dirname, 'ast_fields.py');

const SOURCES = [
  'common.ts', 'accounts.ts', 'profiles.ts', 'workspaces.ts', 'preferences.ts',
  'sources.ts', 'sessions.ts', 'auth.ts', 'activity.ts', 'alerts.ts',
  'feature-flags.ts', 'onboarding.ts', 'users.ts',
  'intake.ts', 'intake-sources.ts', 'intake-events.ts', 'intake-webhooks.ts',
  'verification.ts', 'claims.ts', 'evidence.ts', 'scoring.ts', 'conflicts.ts',
  'intelligence.ts', 'research.ts', 'drafts.ts',
  'content.ts', 'publishing.ts', 'automation.ts', 'analytics.ts', 'training.ts',
  'templates.ts', 'review.ts', 'calendar.ts', 'billing.ts',
];

// index.ts is a barrel re-export; it declares no types of its own.
const NON_MIRRORED = new Set(['index.ts']);

/** Names deliberately declared ahead of real wiring — each entry's own file
 * already documents why it has zero real references today. Anything NOT in
 * this set that the unused-export check flags is a real drift candidate:
 * either wire it in or remove it (see claims.ts/ClaimListResponse,
 * drafts.ts/ContentCounts+GenerateRequest, intake.ts/NormalizedItemView, and
 * workspaces.ts/ChatMessagesListResponse for the precedent of removal). */
const KNOWN_UNWIRED = new Set([
  // auth.ts: "interface only in Phase 2 — endpoints return 501".
  'MfaSetupResponse',
  // intake-webhooks.ts: "Used as documentation of the wire shape; not
  // consumed by mobile in Batch 1."
  'WebhookEnvelope',
  // intake-events.ts: describes the real outbox payload emitted by
  // intake/service.py's enqueue_event() call, which currently hand-builds
  // the matching dict inline rather than constructing this class — a real
  // follow-up candidate (wire the event producer to it), not dead code.
  'IntakeItemReceived',
]);

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
// TS interface extraction (real AST, via the `typescript` package — regex
// cannot safely handle nested braces/generics/extends).
// ---------------------------------------------------------------------------

export interface TsField {
  name: string;
  optional: boolean;
  type: string;
}

export interface TsInterfaceInfo {
  fields: TsField[];
  extends: string[];
}

/** Extract every exported `interface Name { ... }` (and its `extends`
 *  clause) from a TS source file. */
export function extractTsInterfaces(source: string, fileName: string): Map<string, TsInterfaceInfo> {
  const out = new Map<string, TsInterfaceInfo>();
  const sf = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true);
  function visit(node: ts.Node) {
    if (ts.isInterfaceDeclaration(node)) {
      const isExported = (ts.getCombinedModifierFlags(node as unknown as ts.Declaration) & ts.ModifierFlags.Export) !== 0;
      if (isExported) {
        const fields: TsField[] = [];
        for (const member of node.members) {
          if (ts.isPropertySignature(member) && member.name && member.type) {
            fields.push({
              name: member.name.getText(sf),
              optional: !!member.questionToken,
              type: member.type.getText(sf),
            });
          }
        }
        const extendsClause = (node.heritageClauses ?? [])
          .flatMap((h) => h.types.map((t) => t.expression.getText(sf)));
        out.set(node.name.text, { fields, extends: extendsClause });
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
  return out;
}

/** Broad net for the unused-export check: every exported interface or type
 *  alias name, regardless of RHS shape (pure unions, object types, etc). */
export function extractAllExportedTsNames(source: string): string[] {
  const out: string[] = [];
  for (const m of source.matchAll(/^export (?:interface|type) (\w+)/gm)) out.push(m[1]);
  return out;
}

/** Resolve an interface's OWN + inherited (via `extends`) fields, own fields
 *  winning on name collision. */
export function resolveTsFields(
  name: string,
  map: Map<string, TsInterfaceInfo>,
  seen: Set<string> = new Set(),
): TsField[] {
  if (seen.has(name)) return [];
  seen.add(name);
  const entry = map.get(name);
  if (!entry) return [];
  const merged = new Map<string, TsField>();
  for (const base of entry.extends) {
    for (const f of resolveTsFields(base, map, seen)) merged.set(f.name, f);
  }
  for (const f of entry.fields) merged.set(f.name, f);
  return [...merged.values()];
}

// ---------------------------------------------------------------------------
// Python class field extraction (real AST, via ast_fields.py — a tiny
// companion script that uses Python's own `ast` module, the same one the
// syntax probe below already relies on).
// ---------------------------------------------------------------------------

export interface PyField {
  name: string;
  alias: string | null;
  type: string;
  optional: boolean;
}

export interface PyClassInfo {
  fields: PyField[];
  bases: string[];
}

function runPython(args: string): string {
  try {
    return execSync(`python3 ${args}`, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
  } catch {
    return execSync(`python ${args}`, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
  }
}

/** Invoke ast_fields.py against the pydantic mirror and parse its JSON. */
export function extractPyClasses(targetPath: string): Map<string, PyClassInfo> {
  const forward = targetPath.replace(/\\/g, '/');
  const scriptForward = AST_FIELDS_SCRIPT.replace(/\\/g, '/');
  const json = runPython(`"${scriptForward}" "${forward}"`);
  const raw: Record<string, { bases: string[]; fields: PyField[] }> = JSON.parse(json);
  const out = new Map<string, PyClassInfo>();
  for (const [name, info] of Object.entries(raw)) {
    if (name === '_Base') continue; // the pydantic ConfigDict wrapper, not a mirrored type
    out.set(name, { fields: info.fields, bases: info.bases });
  }
  return out;
}

/** Resolve a class's OWN + inherited (via non-_Base/Generic bases) fields,
 *  own fields winning on name collision. */
export function resolvePyFields(
  name: string,
  map: Map<string, PyClassInfo>,
  seen: Set<string> = new Set(),
): PyField[] {
  if (seen.has(name)) return [];
  seen.add(name);
  const entry = map.get(name);
  if (!entry) return [];
  const merged = new Map<string, PyField>();
  for (const base of entry.bases) {
    if (base === '_Base' || base === 'Generic') continue;
    for (const f of resolvePyFields(base, map, seen)) merged.set(f.name, f);
  }
  for (const f of entry.fields) merged.set(f.name, f);
  return [...merged.values()];
}

// ---------------------------------------------------------------------------
// (d) Interface field diff: presence (always compared) + a bounded scalar
// type-shape check (only when both sides reduce to a bare, possibly
// array-wrapped, identifier — everything else is intentionally skipped).
// ---------------------------------------------------------------------------

const TS_TO_PY_BASE: Record<string, string[]> = {
  string: ['str'],
  Id: ['str'],
  Cursor: ['str'],
  Timestamp: ['datetime', 'str'],
  number: ['int', 'float'],
  boolean: ['bool'],
  any: ['Any'],
  unknown: ['Any'],
};

/** A "simple" type is a bare identifier, optionally array-wrapped
 *  (`Foo`, `Foo[]`, `Foo[][]`). Unions, inline object types `{...}`, and
 *  generics `<...>` are NOT simple — returns null so callers skip comparison
 *  rather than guess. */
export function parseSimpleTsType(type: string): { base: string; depth: number } | null {
  let t = type.trim();
  if (/[{<|]/.test(t)) return null;
  let depth = 0;
  while (t.endsWith('[]')) { depth++; t = t.slice(0, -2).trim(); }
  if (!/^\w+$/.test(t)) return null;
  return { base: t, depth };
}

/** Same idea on the Python side: a bare identifier, optionally wrapped in
 *  `list[...]`. Unions (`X | None`), dict/Record, and Any-of-generics are
 *  NOT simple — returns null so callers skip comparison rather than guess. */
export function parseSimplePyType(type: string): { base: string; depth: number } | null {
  let t = type.trim();
  if (/[|{,]/.test(t)) return null;
  let depth = 0;
  while (t.startsWith('list[') && t.endsWith(']')) { depth++; t = t.slice(5, -1).trim(); }
  if (!/^\w+$/.test(t)) return null;
  return { base: t, depth };
}

/** Returns a human-readable conflict description if both sides are simple
 *  AND incompatible; null if compatible; undefined if not safely comparable
 *  (one or both sides too complex — caller should skip, not flag). */
export function simpleTypeConflict(tsType: string, pyType: string): string | null | undefined {
  const a = parseSimpleTsType(tsType);
  const b = parseSimplePyType(pyType);
  if (!a || !b) return undefined;
  if (a.depth !== b.depth) return `array-depth ${a.depth} vs ${b.depth}`;
  const allowed = TS_TO_PY_BASE[a.base];
  if (allowed) return allowed.includes(b.base) ? null : `${a.base} vs ${b.base}`;
  return a.base === b.base ? null : `${a.base} vs ${b.base}`;
}

export interface FieldDiff {
  name: string;
  missingPyCounterpart: boolean;
  missingInPython: string[];
  missingInTs: string[];
  typeConflicts: { field: string; ts: string; py: string; reason: string }[];
}

/** Compare every TS interface's resolved field set to its same-named Python
 *  class's resolved field set. Field presence is always compared; type
 *  shape only when both sides parse as "simple" (see above). */
export function diffInterfaceFields(
  tsInterfaces: Map<string, TsInterfaceInfo>,
  pyClasses: Map<string, PyClassInfo>,
): FieldDiff[] {
  const diffs: FieldDiff[] = [];
  for (const [name] of tsInterfaces) {
    if (!pyClasses.has(name)) {
      diffs.push({ name, missingPyCounterpart: true, missingInPython: [], missingInTs: [], typeConflicts: [] });
      continue;
    }
    const tsFields = resolveTsFields(name, tsInterfaces);
    const pyFields = resolvePyFields(name, pyClasses);
    const pyByKey = new Map(pyFields.map((f) => [f.alias ?? f.name, f]));
    const tsKeys = new Set(tsFields.map((f) => f.name));
    const missingInPython = tsFields.filter((f) => !pyByKey.has(f.name)).map((f) => f.name).sort();
    const missingInTs = pyFields.filter((f) => !tsKeys.has(f.alias ?? f.name))
      .map((f) => f.alias ?? f.name).sort();
    const typeConflicts: FieldDiff['typeConflicts'] = [];
    for (const f of tsFields) {
      const py = pyByKey.get(f.name);
      if (!py) continue;
      const reason = simpleTypeConflict(f.type, py.type);
      if (reason) typeConflicts.push({ field: f.name, ts: f.type, py: py.type, reason });
    }
    if (missingInPython.length > 0 || missingInTs.length > 0 || typeConflicts.length > 0) {
      diffs.push({ name, missingPyCounterpart: false, missingInPython, missingInTs, typeConflicts });
    }
  }
  return diffs;
}

function formatFieldDiff(d: FieldDiff): string {
  if (d.missingPyCounterpart) {
    return `  ${d.name}: no Python class of this name`;
  }
  const bits: string[] = [];
  if (d.missingInPython.length > 0) bits.push(`fields in TS but not Python: ${d.missingInPython.join(', ')}`);
  if (d.missingInTs.length > 0) bits.push(`fields in Python but not TS: ${d.missingInTs.join(', ')}`);
  for (const c of d.typeConflicts) bits.push(`${c.field}: ts='${c.ts}' vs py='${c.py}' (${c.reason})`);
  return `  ${d.name}: ${bits.join('; ')}`;
}

// ---------------------------------------------------------------------------
// (e) Unused-export check: reachability over a reference graph built from
// field types + extends/bases, seeded by real occurrences outside the mirror.
// ---------------------------------------------------------------------------

/** Tokenize free-form type/base text and keep only tokens that are names we
 *  know about (interface/type/class names) — this is how a field of type
 *  `list[Claim]` or `Claim[]` produces an edge to `Claim`. */
export function referencedNames(text: string, known: ReadonlySet<string>): Set<string> {
  const out = new Set<string>();
  for (const m of text.matchAll(/[A-Za-z_]\w*/g)) {
    if (known.has(m[0])) out.add(m[0]);
  }
  return out;
}

/** Build the composition graph: name -> set of other known names its own
 *  declaration (fields + extends/bases) mentions. */
export function buildReferenceGraph(
  tsInterfaces: Map<string, TsInterfaceInfo>,
  pyClasses: Map<string, PyClassInfo>,
  known: ReadonlySet<string>,
): Map<string, Set<string>> {
  const graph = new Map<string, Set<string>>();
  const addEdge = (from: string, to: string) => {
    if (from === to) return;
    if (!graph.has(from)) graph.set(from, new Set());
    graph.get(from)!.add(to);
  };
  for (const [name, info] of tsInterfaces) {
    for (const base of info.extends) if (known.has(base)) addEdge(name, base);
    for (const f of info.fields) for (const ref of referencedNames(f.type, known)) addEdge(name, ref);
  }
  for (const [name, info] of pyClasses) {
    for (const base of info.bases) if (known.has(base)) addEdge(name, base);
    for (const f of info.fields) for (const ref of referencedNames(f.type, known)) addEdge(name, ref);
  }
  return graph;
}

/** Scan a set of {path, content} files once each for occurrences of any
 *  known name, stopping early once every name has been found at least
 *  once. Pure function so the self-test can supply synthetic files. */
export function findExternalUses(
  names: Iterable<string>,
  files: { content: string }[],
): Set<string> {
  const remaining = new Set(names);
  const used = new Set<string>();
  for (const file of files) {
    if (remaining.size === 0) break;
    for (const m of file.content.matchAll(/[A-Za-z_]\w*/g)) {
      if (remaining.has(m[0])) { used.add(m[0]); remaining.delete(m[0]); }
    }
  }
  return used;
}

/** BFS closure over the reference graph starting from the externally-used
 *  seeds — anything reachable from a real external use counts as used too
 *  (e.g. a private Python helper class only ever referenced as a field type
 *  on a class that IS used externally). */
export function reachableFrom(seeds: Iterable<string>, graph: Map<string, Set<string>>): Set<string> {
  const seen = new Set(seeds);
  const queue = [...seen];
  while (queue.length > 0) {
    const cur = queue.pop()!;
    for (const next of graph.get(cur) ?? []) {
      if (!seen.has(next)) { seen.add(next); queue.push(next); }
    }
  }
  return seen;
}

/** Names in `allNames` that are neither directly used nor transitively
 *  reachable from something that is, excluding KNOWN_UNWIRED. */
export function findUnusedExports(
  allNames: Iterable<string>,
  graph: Map<string, Set<string>>,
  externallyUsed: Set<string>,
  knownUnwired: ReadonlySet<string> = new Set(),
): string[] {
  const reachable = reachableFrom(externallyUsed, graph);
  return [...allNames].filter((n) => !reachable.has(n) && !knownUnwired.has(n)).sort();
}

function walkFiles(root: string, extensions: string[]): { path: string; content: string }[] {
  const exclude = new Set(['node_modules', '.expo', 'dist', 'build', '__pycache__', '.git']);
  const out: { path: string; content: string }[] = [];
  if (!existsSync(root)) return out;
  const stack = [root];
  while (stack.length > 0) {
    const dir = stack.pop()!;
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (exclude.has(entry.name)) continue;
      const full = resolve(dir, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (extensions.some((ext) => entry.name.endsWith(ext))) {
        out.push({ path: full, content: readFileSync(full, 'utf-8') });
      }
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// Self-test: prove every check actually catches mismatches before trusting it
// ---------------------------------------------------------------------------

function fail(msg: string): never {
  console.error(`SELF-TEST FAILED: ${msg}`);
  process.exit(1);
}

function testUnionDiffCatchesMismatchMissingAliasAndClean(): void {
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
  const tsUnions = extractTsUnions(tsFixture);
  const pyLiterals = extractPyLiterals(pyFixture);
  if (tsUnions.size !== 2) fail(`expected 2 TS unions (Id skipped), got ${tsUnions.size}`);
  if (pyLiterals.size !== 3) fail(`expected 3 Python Literals, got ${pyLiterals.size}`);
  const diffs = diffUnions(tsUnions, pyLiterals);
  if (diffs.length !== 1) fail(`expected exactly 1 mismatch, got ${diffs.length}`);
  const d = diffs[0];
  if (d.name !== 'Health') fail(`expected mismatch on Health, got ${d.name}`);
  if (d.onlyInTs.join(',') !== 'disabled') fail(`expected 'disabled' only-in-TS, got [${d.onlyInTs}]`);
  if (d.onlyInPy.join(',') !== 'offline') fail(`expected 'offline' only-in-Python, got [${d.onlyInPy}]`);
  const pyWithout = new Map(pyLiterals);
  pyWithout.delete('Health');
  const missing = diffUnions(tsUnions, pyWithout);
  if (!missing.some((x) => x.name === 'Health' && x.missingPyAlias)) {
    fail('expected missing-Python-alias detection for Health');
  }
  const clean = diffUnions(tsUnions, extractPyLiterals(
    'Health = Literal["healthy", "degraded", "disabled"]\nKind = Literal["gmail", "rss"]',
  ));
  if (clean.length !== 0) fail(`expected clean fixture to pass, got ${clean.length} diffs`);
  console.warn('  ok: union diff catches mismatch + missing-alias, passes clean fixture');
}

function testInterfaceFieldDiffCatchesGenuineMismatch(): void {
  // Widget gains a field TS-only, loses a field Python-only, and its `age`
  // field disagrees on base scalar type (number vs str) — three distinct,
  // unambiguous mismatch kinds in one fixture.
  const tsSource = `
export interface Widget {
  id: string;
  age: number;
  extraTsOnly: string;
}
`;
  const tsInterfaces = extractTsInterfaces(tsSource, 'widget.ts');
  const pyClasses = new Map<string, PyClassInfo>([
    ['Widget', {
      bases: ['_Base'],
      fields: [
        { name: 'id', alias: null, type: 'str', optional: false },
        { name: 'age', alias: null, type: 'str', optional: false },
        { name: 'extra_python_only', alias: 'extraPythonOnly', type: 'str', optional: false },
      ],
    }],
  ]);
  const diffs = diffInterfaceFields(tsInterfaces, pyClasses);
  if (diffs.length !== 1) fail(`expected exactly 1 interface diff, got ${diffs.length}`);
  const d = diffs[0];
  if (d.missingInPython.join(',') !== 'extraTsOnly') {
    fail(`expected extraTsOnly missing in Python, got [${d.missingInPython}]`);
  }
  if (d.missingInTs.join(',') !== 'extraPythonOnly') {
    fail(`expected extraPythonOnly missing in TS, got [${d.missingInTs}]`);
  }
  if (d.typeConflicts.length !== 1 || d.typeConflicts[0].field !== 'age') {
    fail(`expected exactly 1 type conflict on 'age', got ${JSON.stringify(d.typeConflicts)}`);
  }
  console.warn('  ok: interface field diff catches missing-in-Python, missing-in-TS, and a type conflict');
}

function testInterfaceFieldDiffCleanOnRealPatterns(): void {
  // Reproduces this codebase's actual conventions: nullable-but-required
  // fields (`X | null` <-> `X | None = Field(default=None, ...)`), a
  // defaulted-but-non-nullable field (`sourceDeleted`-style), extends-chain
  // inheritance, and an inline TS object type mirrored by a named Python
  // helper class (the ClaimListResponse/_ClaimListMeta shape) — none of
  // these are drift, and the diff must report zero.
  const tsSource = `
export interface Base {
  id: string;
}
export interface Widget extends Base {
  nullableRequired: string | null;
  defaultedBool: boolean;
  meta: { pagination: string };
}
`;
  const tsInterfaces = extractTsInterfaces(tsSource, 'widget.ts');
  const pyClasses = new Map<string, PyClassInfo>([
    ['Base', { bases: ['_Base'], fields: [{ name: 'id', alias: null, type: 'str', optional: false }] }],
    ['Widget', {
      bases: ['Base'],
      fields: [
        { name: 'nullable_required', alias: 'nullableRequired', type: 'str | None', optional: true },
        { name: 'defaulted_bool', alias: 'defaultedBool', type: 'bool', optional: true },
        { name: 'meta', alias: null, type: '_WidgetMeta', optional: false },
      ],
    }],
  ]);
  const diffs = diffInterfaceFields(tsInterfaces, pyClasses);
  if (diffs.length !== 0) fail(`expected zero diffs on real-pattern fixture, got ${JSON.stringify(diffs)}`);
  console.warn('  ok: interface field diff stays clean on nullable/defaulted/extends/inline-object patterns');
}

function testUnusedExportCatchesGenuinelyDeadType(): void {
  const known = new Set(['UsedType', 'DeadType']);
  const tsInterfaces = new Map<string, TsInterfaceInfo>([
    ['UsedType', { fields: [{ name: 'id', optional: false, type: 'string' }], extends: [] }],
    ['DeadType', { fields: [{ name: 'id', optional: false, type: 'string' }], extends: [] }],
  ]);
  const graph = buildReferenceGraph(tsInterfaces, new Map(), known);
  const files = [{ content: 'import { UsedType } from "@oryx/shared-types";' }];
  const used = findExternalUses(known, files);
  const unused = findUnusedExports(known, graph, used);
  if (unused.join(',') !== 'DeadType') fail(`expected only DeadType flagged unused, got [${unused}]`);
  console.warn('  ok: unused-export check catches a genuinely unreferenced type');
}

function testUnusedExportCleanWhenReachableViaCompositionOrAllowlist(): void {
  // ParentType is used externally; ChildHelper is only ever referenced as a
  // field type on ParentType (the _ClaimListMeta pattern) — must NOT be
  // flagged. StubType has zero references anywhere but is in the allowlist
  // (the MfaSetupResponse/WebhookEnvelope pattern) — must also NOT be flagged.
  const known = new Set(['ParentType', 'ChildHelper', 'StubType']);
  const pyClasses = new Map<string, PyClassInfo>([
    ['ParentType', { bases: ['_Base'], fields: [{ name: 'meta', alias: null, type: 'ChildHelper', optional: false }] }],
    ['ChildHelper', { bases: ['_Base'], fields: [] }],
    ['StubType', { bases: ['_Base'], fields: [] }],
  ]);
  const graph = buildReferenceGraph(new Map(), pyClasses, known);
  const files = [{ content: 'x = ParentType(meta=None)' }];
  const used = findExternalUses(known, files);
  const unused = findUnusedExports(known, graph, used, new Set(['StubType']));
  if (unused.length !== 0) fail(`expected zero unused (composition + allowlist), got [${unused}]`);
  console.warn('  ok: unused-export check stays clean for composition-reachable and allowlisted names');
}

function testReconstructedChatMessagesListResponseIncident(): void {
  // The actual incident: TS interface and Python class declared IDENTICALLY
  // (so field-diff sees zero drift) but referenced NOWHERE — not by any
  // mobile file, not by any backend router, not by any other shared type.
  const tsSource = `
export interface ChatMessagesListResponse {
  messages: string;
  meta: string;
}
`;
  const tsInterfaces = extractTsInterfaces(tsSource, 'workspaces.ts');
  const pyClasses = new Map<string, PyClassInfo>([
    ['ChatMessagesListResponse', {
      bases: ['_Base'],
      fields: [
        { name: 'messages', alias: null, type: 'str', optional: false },
        { name: 'meta', alias: null, type: 'str', optional: false },
      ],
    }],
  ]);

  const fieldDiffs = diffInterfaceFields(tsInterfaces, pyClasses);
  if (fieldDiffs.length !== 0) {
    fail(`expected the field-diff to see ZERO drift on the reconstructed incident (both sides match identically) — this is the point: field-diff alone cannot catch it. Got ${JSON.stringify(fieldDiffs)}`);
  }

  const known = new Set(['ChatMessagesListResponse']);
  const graph = buildReferenceGraph(tsInterfaces, pyClasses, known);
  // No mobile/backend/test file anywhere ever mentions the name — exactly
  // the real incident (verified via repo-wide grep before this type was
  // removed in the same wave that introduced it).
  const files: { content: string }[] = [{ content: 'some unrelated router code' }];
  const used = findExternalUses(known, files);
  const unused = findUnusedExports(known, graph, used);
  if (unused.join(',') !== 'ChatMessagesListResponse') {
    fail(`expected unused-export check to catch the reconstructed incident, got [${unused}]`);
  }
  console.warn('  ok: reconstructed ChatMessagesListResponse incident — field-diff sees no drift, unused-export catches it');
}

function selfTest(): void {
  testUnionDiffCatchesMismatchMissingAliasAndClean();
  testInterfaceFieldDiffCatchesGenuineMismatch();
  testInterfaceFieldDiffCleanOnRealPatterns();
  testUnusedExportCatchesGenuinelyDeadType();
  testUnusedExportCleanWhenReachableViaCompositionOrAllowlist();
  testReconstructedChatMessagesListResponseIncident();
  console.warn('self-test passed: union diff, interface field diff, and unused-export checks all verified.');
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

  // Parse every TS source once; reused by (c), (d), and (e).
  const tsUnions = new Map<string, Set<string>>();
  const tsUnionHome = new Map<string, string>();
  const tsInterfaces = new Map<string, TsInterfaceInfo>();
  const allTsNames = new Set<string>();
  for (const src of SOURCES) {
    const content = readFileSync(resolve(SRC_DIR, src), 'utf-8');
    for (const [name, members] of extractTsUnions(content)) {
      if (tsUnions.has(name)) {
        console.error(`Duplicate exported union alias '${name}' in ${src} and ${tsUnionHome.get(name)}`);
        process.exit(1);
      }
      tsUnions.set(name, members);
      tsUnionHome.set(name, src);
    }
    for (const [name, info] of extractTsInterfaces(content, src)) tsInterfaces.set(name, info);
    for (const name of extractAllExportedTsNames(content)) allTsNames.add(name);
  }

  // (c) semantic union diff.
  const pyLiterals = extractPyLiterals(readFileSync(TARGET, 'utf-8'));
  const unionDiffs = diffUnions(tsUnions, pyLiterals);
  if (unionDiffs.length > 0) {
    console.error('Semantic drift between shared-types unions and Python Literals:');
    for (const d of unionDiffs) console.error(formatDiff(d));
    process.exit(1);
  }
  const pyOnly = [...pyLiterals.keys()].filter((n) => !tsUnions.has(n));
  if (pyOnly.length > 0) {
    console.warn(`note: Python-only Literal aliases (no exported TS alias): ${pyOnly.join(', ')}`);
  }

  // (d) interface field diff.
  const pyClasses = extractPyClasses(TARGET);
  const fieldDiffs = diffInterfaceFields(tsInterfaces, pyClasses);
  if (fieldDiffs.length > 0) {
    console.error('Field-level drift between shared-types interfaces and Python classes:');
    for (const d of fieldDiffs) console.error(formatFieldDiff(d));
    process.exit(1);
  }

  // (e) unused-export check.
  const allPyClassNames = new Set(pyClasses.keys());
  const allNames = new Set([...allTsNames, ...allPyClassNames]);
  const graph = buildReferenceGraph(tsInterfaces, pyClasses, allNames);
  const mobileFiles = walkFiles(resolve(REPO_ROOT, 'apps/mobile/src'), ['.ts', '.tsx']);
  const backendFiles = walkFiles(resolve(REPO_ROOT, 'apps/backend/src'), ['.py'])
    .filter((f) => f.path !== TARGET);
  const backendTestFiles = walkFiles(resolve(REPO_ROOT, 'apps/backend/tests'), ['.py']);
  const externallyUsed = findExternalUses(allNames, [...mobileFiles, ...backendFiles, ...backendTestFiles]);
  const unused = findUnusedExports(allNames, graph, externallyUsed, KNOWN_UNWIRED);
  if (unused.length > 0) {
    console.error(
      'Exported shared-types names with zero real references (mobile, backend, tests) — ' +
      'wire them in, remove them, or add them to KNOWN_UNWIRED with a documented reason:',
    );
    for (const n of unused) console.error(`  ${n}`);
    process.exit(1);
  }

  console.warn(
    `shared-types pydantic mirror present, parses, and ${tsUnions.size} string-literal unions, ` +
    `${tsInterfaces.size} interfaces, and ${allNames.size} exported names ` +
    'all match their Python counterparts with no unused exports.',
  );
}

main();
