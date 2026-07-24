/**
 * Theming Phase B — consumer hygiene (pure source scans, no react-native).
 * The gx split is only complete if every runtime consumer resolves gx through
 * the theme-tracking hook and the old static dark sheet is gone from the
 * design-system surface — a single straggler file would silently keep a dark
 * pocket in light mode, which is exactly the state this wave closes.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const read = (rel: string): string =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8');

/** The 7 runtime gx consumers confirmed by this wave's Phase 0 re-sweep. */
const CONSUMERS = [
  '../components/web/WebSidebar.tsx',
  '../components/web/WebTopBar.tsx',
  '../modules/automation/screens/AutomationHubScreen.tsx',
  '../modules/dashboard/screens/DashboardScreen.tsx',
  '../modules/content/screens/ContentHomeScreen.tsx',
  '../modules/content/components/DraftCard.tsx',
  '../modules/research/components/WorkspaceCard.tsx',
];

test('every gx consumer resolves the sheet through useGx() — no static gx import anywhere', () => {
  for (const rel of CONSUMERS) {
    const source = read(rel);
    assert.ok(source.includes('useGx'), `${rel}: imports the useGx hook`);
    assert.ok(source.includes('useGx()'), `${rel}: calls useGx()`);
    assert.ok(
      !/import\s*\{[^}]*(?<![A-Za-z])gx\b[^}]*\}/.test(source),
      `${rel}: no static gx import from the retired dark sheet`,
    );
    assert.ok(
      !/from\s+['"][^'"]*styles\/genspark['"]/.test(source),
      `${rel}: no deep import of the genspark module`,
    );
  }
});

test('the design-system surface exports the split (gxGeometry/makeGx/useGx) and no longer the static gx', () => {
  const index = read('../../../../packages/design-system/src/index.ts');
  assert.ok(index.includes('gxGeometry'), 'geometry sheet exported');
  assert.ok(index.includes('makeGx'), 'factory exported');
  assert.ok(index.includes('useGx'), 'hook exported');
  assert.ok(!/export\s*\{[^}]*(?<![A-Za-z])gx\b\s*[,}]/.test(index.replace(/gxGeometry/g, '')), 'static gx export gone');
  const genspark = read('../../../../packages/design-system/src/styles/genspark.ts');
  assert.ok(!genspark.includes('export const gx ='), 'the static dark StyleSheet is gone at the source');
});

test('the factory source keeps no inlined color literal for the migrated washes (withAlpha over tokens only)', () => {
  // Comments legitimately QUOTE the CSS source selectors — scan code only.
  const genspark = read('../../../../packages/design-system/src/styles/genspark.ts')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/[^\n]*/g, '');
  // The old sheet inlined these exact rgba channel values; none may survive.
  for (const literal of ['rgba(139,92,246', 'rgba(91,91,245', 'rgba(248,113,113', 'rgba(245,158,11', 'rgba(255,255,255,0.03']) {
    assert.ok(!genspark.includes(literal), `${literal}: re-inlined literal must not survive the split`);
  }
});
