/* eslint-disable no-restricted-syntax --
 * The inline-hex ban keeps colors flowing through tokens; here the hexes ARE
 * the expected values the tokens are pinned against (foundation.test.ts
 * precedent). */
/**
 * Theming Phase A (2026-07-16) — light palette, switch mechanism, and the
 * migration regressions. Source scans follow the established pattern
 * (list.test.ts / home.test.ts); rendered both-mode checks (and the gx
 * deferral regression, which needs the react-native shims) live in
 * themedComponents.test.tsx.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { themes, withAlpha } from '@oryx/design-system/tokens';
import { themeActions, themeReducer } from '../store/slices/theme';
import {
  SEVERITY_AMBER,
  SEVERITY_INDIGO,
  SEVERITY_RED,
} from '../modules/verification/components/severityColors';
import {
  packetStatusColor,
  verificationStatusColor,
} from '../modules/verification/components/statusColors';
import {
  draftStatusColor,
  formatColor,
} from '../modules/content/theme/draftColors';

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const read = (rel: string): string =>
  stripComments(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8'));

// ---- The verified light palette resolves exactly as provided ---------------

test('themes.light carries the owner-provided WCAG-verified palette values exactly', () => {
  const c = themes.light.colors;
  assert.equal(c.bg.primary, '#F7F8FA');
  assert.equal(c.bg.card, '#FFFFFF');
  assert.equal(c.bg.elevated, '#EDEFF3');
  assert.equal(c.text.primary, '#14171C');
  assert.equal(c.accent.amber, '#5B5BF5'); // indigo — unchanged across modes
  assert.equal(c.accent.coral, '#7440D6'); // light-verified violet
  assert.equal(c.semantic.positiveText, '#155A9C');
  assert.equal(c.semantic.positiveSurface, '#E3EFFA');
  assert.equal(c.semantic.danger, '#9E241E');
  assert.equal(c.semantic.warning, '#96640A');
  assert.equal(c.semantic.info, '#17517E');
});

test('light border.default is the derived, contrast-checked #D7DDE5 (1.29:1 vs bg — the dark hairline role, not an inversion)', () => {
  assert.equal(themes.light.colors.border.default, '#D7DDE5');
  assert.equal(themes.light.colors.border.strong, '#C4CDD9');
});

test('themes.dark is byte-identical to the shipped Genspark values (the switch regresses nothing)', () => {
  const c = themes.dark.colors;
  assert.equal(c.bg.primary, '#05070A');
  assert.equal(c.bg.card, '#0A0E14');
  assert.equal(c.text.primary, '#E6EAF2');
  assert.equal(c.border.default, '#1A2330');
  assert.equal(c.accent.coral, '#8B5CF6'); // dark keeps the Genspark violet
  assert.equal(c.semantic.positiveText, '#30A3E9');
  assert.equal(c.semantic.danger, '#F87171');
  assert.equal(themes.dark.gradients.sidebar.from, '#07090D');
});

test('every color token key exists in BOTH modes with a non-empty value (structural parity — no screen can hit an undefined token after a switch)', () => {
  const walk = (obj: Record<string, unknown>, path: string[]): string[][] =>
    Object.entries(obj).flatMap(([k, v]) =>
      typeof v === 'object' && v !== null
        ? walk(v as Record<string, unknown>, [...path, k])
        : [[...path, k]],
    );
  const darkKeys = walk(themes.dark.colors as never, []).map((p) => p.join('.'));
  const lightKeys = walk(themes.light.colors as never, []).map((p) => p.join('.'));
  assert.deepEqual(lightKeys.sort(), darkKeys.sort());
  for (const mode of ['dark', 'light'] as const) {
    for (const path of walk(themes[mode].colors as never, [])) {
      let v: unknown = themes[mode].colors;
      for (const k of path) v = (v as Record<string, unknown>)[k];
      assert.ok(
        typeof v === 'string' && v.length > 0,
        `${mode}.${path.join('.')} resolves to a color string`,
      );
    }
  }
});

test('both modes share one consolidated scrim (the migrated 0.5/0.55/0.60 trio) and each carries a mode-correct glass', () => {
  assert.equal(themes.dark.colors.overlay.scrim, 'rgba(0,0,0,0.55)');
  assert.equal(themes.light.colors.overlay.scrim, 'rgba(0,0,0,0.55)');
  assert.equal(themes.dark.colors.overlay.glass, 'rgba(10,14,20,0.70)');
  assert.equal(themes.light.colors.overlay.glass, 'rgba(255,255,255,0.70)');
});

test('withAlpha composes with light tokens (the migrated badge/track/banner washes resolve in both modes)', () => {
  assert.equal(withAlpha(themes.light.colors.text.tertiary, 0.15), 'rgba(85,96,114,0.15)');
  assert.equal(withAlpha(themes.dark.colors.text.tertiary, 0.15), 'rgba(107,117,136,0.15)');
  assert.equal(withAlpha(themes.light.colors.semantic.danger, 0.12), 'rgba(158,36,30,0.12)');
  assert.equal(withAlpha(themes.dark.colors.semantic.danger, 0.12), 'rgba(248,113,113,0.12)');
});

// ---- The switch mechanism ---------------------------------------------------

test('theme slice: modeSet actually flips the mode (the Phase-1 empty reducer is gone)', () => {
  const dark = themeReducer(undefined, { type: '@@INIT' });
  assert.equal(dark.mode, 'dark');
  const light = themeReducer(dark, themeActions.modeSet('light'));
  assert.equal(light.mode, 'light');
  assert.equal(themeReducer(light, themeActions.modeSet('dark')).mode, 'dark');
});

test('themes registry maps each mode to a theme that self-reports it', () => {
  assert.equal(themes.dark.mode, 'dark');
  assert.equal(themes.light.mode, 'light');
});

// ---- Migrated files carry no color literals any more ------------------------

test('no migrated file retains a hardcoded rgba()/hex color literal', () => {
  const migrated = [
    '../modules/verification/screens/ClaimDetailScreen.tsx',
    '../modules/verification/screens/ConflictReviewScreen.tsx',
    '../modules/verification/screens/IntelligenceObjectDetailScreen.tsx',
    '../modules/research/screens/IntelligenceObjectPickerScreen.tsx',
    '../modules/verification/components/EpistemicTypeBadge.tsx',
    '../modules/verification/components/ConflictWarningBanner.tsx',
    '../modules/verification/components/ConfidenceMeter.tsx',
    '../components/web/WebShell.tsx',
    '../components/web/WebSearchOverlay.tsx',
    '../modules/content/screens/DraftEditorScreen.tsx',
    '../modules/content/screens/PublishTargetScreen.tsx',
  ];
  for (const rel of migrated) {
    const source = read(rel);
    assert.ok(!/rgba?\(/.test(source), `${rel}: no rgba()/rgb() literals`);
    assert.ok(!/'#[0-9a-fA-F]{3,8}'/.test(source), `${rel}: no hex literals`);
  }
});

// ---- Phase 0.2: spec-locked palettes stay mode-invariant --------------------

test('status/severity/draft palettes are spec-locked and identical regardless of theme (their own headers fix these hexes)', () => {
  // These functions never read the theme — same output whatever the mode.
  assert.equal(verificationStatusColor('verified'), '#22C55E');
  assert.equal(verificationStatusColor('analyst_rejected'), '#EF4444');
  assert.equal(packetStatusColor('ready'), '#22C55E');
  assert.equal(SEVERITY_RED, '#EF4444');
  assert.equal(SEVERITY_AMBER, '#F59E0B');
  assert.equal(SEVERITY_INDIGO, '#6366F1');
  assert.equal(draftStatusColor('published'), '#00D4C8');
  assert.equal(formatColor('tweet_thread'), '#60A5FA');
});

// ---- Explicit deferrals stay untouched --------------------------------------

test('ErrorBoundary stays permanently theme-invariant: no theme imports, own hexes intact, mounted OUTSIDE ThemeProvider', () => {
  const boundary = read('../components/ErrorBoundary.tsx');
  assert.ok(!boundary.includes('useTheme'), 'ErrorBoundary never reads the theme');
  assert.ok(!boundary.includes('@oryx/design-system'), 'no design-system import at all');
  assert.ok(boundary.includes("'#0A0A0F'"), 'keeps its own hardcoded surface');

  const providers = read('../providers/AppProviders.tsx');
  const boundaryAt = providers.indexOf('<ErrorBoundary>');
  const themedAt = providers.indexOf('<ThemedProvider>');
  assert.ok(boundaryAt !== -1 && themedAt !== -1, 'both mounts present');
  assert.ok(
    boundaryAt < themedAt,
    'ErrorBoundary wraps the theme system, never the reverse — it must render even if theming breaks',
  );
});
