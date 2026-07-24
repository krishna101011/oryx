/* eslint-disable no-restricted-syntax --
 * The inline-hex ban keeps colors flowing through tokens; here the hexes ARE
 * the expected values the tokens are pinned against (foundation.test.ts
 * precedent). */
/**
 * Theming Phase A — rendered both-mode proof: the REAL migrated verification
 * components mount under ThemeProvider with each theme and resolve their
 * migrated washes/tracks to that mode's tokens (no residue of the old
 * rgba(127,127,127,…)/rgba(239,68,68,…) literals in either mode). Also hosts
 * the theming Phase B gx-split proofs (gx needs the react-native shims).
 *
 * Same harness rules as automation/expandOnPress.test.tsx: register the
 * platform shims BEFORE anything importing react-native, and load every
 * runtime module through the same require function (one CJS instance).
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import type * as ReactNS from 'react';
import type * as TestRendererNS from 'react-test-renderer';
import type { ReactTestRenderer } from 'react-test-renderer';
import type * as DesignSystemNS from '@oryx/design-system';
import type * as BadgeNS from '../modules/verification/components/EpistemicTypeBadge';
import type * as BannerNS from '../modules/verification/components/ConflictWarningBanner';
import type * as MeterNS from '../modules/verification/components/ConfidenceMeter';

const req = createRequire(import.meta.url);
req('../test/shims/register.js');

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

type Mode = 'dark' | 'light';

function renderInMode(mode: Mode, element: ReactNS.ReactElement): ReactTestRenderer {
  const React = req('react') as typeof ReactNS;
  const { create, act } = req('react-test-renderer') as typeof TestRendererNS;
  const { ThemeProvider, themes } = req('@oryx/design-system') as typeof DesignSystemNS;
  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(
      React.createElement(ThemeProvider, { theme: themes[mode], children: element }),
    );
  });
  return tree;
}

/** Collect every backgroundColor/borderColor in the rendered style tree. */
function colorsOf(tree: ReactTestRenderer): string[] {
  const out: string[] = [];
  const visit = (style: unknown): void => {
    if (Array.isArray(style)) return style.forEach(visit);
    if (style && typeof style === 'object') {
      const s = style as Record<string, unknown>;
      for (const key of ['backgroundColor', 'borderColor']) {
        if (typeof s[key] === 'string') out.push(s[key] as string);
      }
    }
  };
  for (const node of tree.root.findAll(() => true)) visit(node.props?.style);
  return out;
}

test('EpistemicTypeBadge resolves its wash from each mode’s text.tertiary — never the retired grey literal', () => {
  const React = req('react') as typeof ReactNS;
  const { act } = req('react-test-renderer') as typeof TestRendererNS;
  const { themes, withAlpha } = req('@oryx/design-system') as typeof DesignSystemNS;
  const { EpistemicTypeBadge } = req(
    '../modules/verification/components/EpistemicTypeBadge',
  ) as typeof BadgeNS;

  for (const mode of ['dark', 'light'] as const) {
    const tree = renderInMode(mode, React.createElement(EpistemicTypeBadge, { type: 'speculation' }));
    const colors = colorsOf(tree);
    assert.ok(
      colors.includes(withAlpha(themes[mode].colors.text.tertiary, 0.15)),
      `${mode}: badge wash tracks text.tertiary`,
    );
    assert.ok(!colors.includes('rgba(127,127,127,0.15)'), `${mode}: old literal gone`);
    act(() => tree.unmount());
  }
});

test('ConflictWarningBanner’s wash tracks semantic.danger per mode (dark #F87171 wash, light #9E241E wash)', () => {
  const React = req('react') as typeof ReactNS;
  const { act } = req('react-test-renderer') as typeof TestRendererNS;
  const { themes, withAlpha } = req('@oryx/design-system') as typeof DesignSystemNS;
  const { ConflictWarningBanner } = req(
    '../modules/verification/components/ConflictWarningBanner',
  ) as typeof BannerNS;

  const washes: Record<Mode, string> = { dark: '', light: '' };
  for (const mode of ['dark', 'light'] as const) {
    const tree = renderInMode(mode, React.createElement(ConflictWarningBanner));
    const expected = withAlpha(themes[mode].colors.semantic.danger, 0.12);
    assert.ok(colorsOf(tree).includes(expected), `${mode}: banner wash is danger@0.12`);
    washes[mode] = expected;
    act(() => tree.unmount());
  }
  assert.notEqual(washes.dark, washes.light, 'the wash really changes with the mode');
});

test('ConfidenceMeter: theme-aware track per mode, spec-locked SEVERITY_INDIGO fill in BOTH modes', () => {
  const React = req('react') as typeof ReactNS;
  const { act } = req('react-test-renderer') as typeof TestRendererNS;
  const { themes, withAlpha } = req('@oryx/design-system') as typeof DesignSystemNS;
  const { ConfidenceMeter } = req(
    '../modules/verification/components/ConfidenceMeter',
  ) as typeof MeterNS;

  for (const mode of ['dark', 'light'] as const) {
    const tree = renderInMode(mode, React.createElement(ConfidenceMeter, { score: 0.62 }));
    const colors = colorsOf(tree);
    assert.ok(
      colors.includes(withAlpha(themes[mode].colors.text.tertiary, 0.2)),
      `${mode}: track wash tracks text.tertiary`,
    );
    assert.ok(colors.includes('#6366F1'), `${mode}: fill stays the spec-locked indigo`);
    act(() => tree.unmount());
  }
});

// ---- theming Phase B: the gx split (was the Phase A dark-literal canary) ----

test('gx factory resolves the former dark pockets per mode: topbar, navBadge, chrome borders', () => {
  const { makeGx, themes } = req('@oryx/design-system') as typeof DesignSystemNS;
  // dark keeps the exact shipped Genspark values (the split regresses nothing)
  const dark = makeGx(themes.dark);
  assert.equal((dark.topbar as { backgroundColor?: string }).backgroundColor, '#05070A');
  assert.equal((dark.topbar as { borderBottomColor?: string }).borderBottomColor, '#1A2330');
  assert.equal((dark.navBadge as { backgroundColor?: string }).backgroundColor, '#161D28');
  assert.equal((dark.sidebar as { borderRightColor?: string }).borderRightColor, '#1A2330');
  // light resolves the SAME keys to the Phase A light ramp — the mixed state is closed
  const light = makeGx(themes.light);
  assert.equal((light.topbar as { backgroundColor?: string }).backgroundColor, '#F7F8FA');
  assert.equal((light.topbar as { borderBottomColor?: string }).borderBottomColor, '#D7DDE5');
  assert.equal((light.navBadge as { backgroundColor?: string }).backgroundColor, '#E2E6EC');
  assert.equal((light.sidebar as { borderRightColor?: string }).borderRightColor, '#D7DDE5');
});

test('gx washes rebuild from ACTIVE-theme tokens in both modes (chips, navItemActive, aiBtn), never re-inlined literals', () => {
  const { makeGx, themes, withAlpha } = req('@oryx/design-system') as typeof DesignSystemNS;
  for (const mode of ['dark', 'light'] as const) {
    const t = themes[mode];
    const gx = makeGx(t);
    const c = (k: object, prop: string): string => (k as Record<string, string>)[prop]!;
    assert.equal(c(gx.chipTeal, 'borderColor'), withAlpha(t.colors.accent.teal, 0.3), `${mode}: teal wash`);
    assert.equal(c(gx.chipIndigo, 'backgroundColor'), withAlpha(t.colors.accent.slateBlue, 0.06), `${mode}: indigo wash`);
    assert.equal(c(gx.chipNeg, 'borderColor'), withAlpha(t.colors.semantic.danger, 0.3), `${mode}: neg wash`);
    assert.equal(c(gx.chipWarn, 'backgroundColor'), withAlpha(t.colors.semantic.warning, 0.06), `${mode}: warn wash`);
    assert.equal(c(gx.navItemActive, 'backgroundColor'), withAlpha(t.colors.accent.slateBlue, 0.1), `${mode}: active nav wash`);
    assert.equal(c(gx.aiBtn, 'borderColor'), withAlpha(t.colors.accent.plum, 0.3), `${mode}: aiBtn wash`);
    // the one cross-token read resolves through the ACTIVE theme, not dark
    assert.equal(c(gx.chipTealText, 'color'), t.colors.semantic.positiveText, `${mode}: chipTealText reads the active positiveText`);
    // btnPrimaryText: mode-invariant white-on-accent, resolved through the theme
    assert.equal(c(gx.btnPrimaryText, 'color'), '#FFFFFF', `${mode}: white on accent (styles.css:281)`);
  }
});

test('gx geometry keys are static and shared between modes; the merged sheet carries 13 geometry + 28 themed keys', () => {
  const { gxGeometry, makeGx, themes } = req('@oryx/design-system') as typeof DesignSystemNS;
  assert.equal(Object.keys(gxGeometry).length, 13);
  const dark = makeGx(themes.dark);
  const light = makeGx(themes.light);
  for (const key of Object.keys(gxGeometry) as (keyof typeof gxGeometry)[]) {
    assert.equal(dark[key], gxGeometry[key], `${String(key)}: dark shares the static style`);
    assert.equal(light[key], gxGeometry[key], `${String(key)}: light shares the static style`);
  }
  assert.equal(Object.keys(dark).length, 13 + 28);
  // the factory is cached per theme — referentially stable across calls
  assert.equal(makeGx(themes.dark), dark);
  assert.equal(makeGx(themes.light), light);
  assert.notEqual(dark.topbar, light.topbar);
});

test('the 17 retired gx keys are genuinely gone (not just unused), and the old static gx export no longer exists', () => {
  const ds = req('@oryx/design-system') as typeof DesignSystemNS & { gx?: unknown };
  assert.equal(ds.gx, undefined, 'the static dark gx export is retired');
  const sheet = ds.makeGx(ds.themes.dark) as Record<string, unknown>;
  const retired = [
    'card', 'cardHead', 'kpi', 'kpiLabel', 'kpiVal', 'chipViolet', 'chipVioletText',
    'meter', 'navDot', 'pageHead', 'tblHeadCell', 'tblCell', 'heatCell',
    'calDay', 'calToday', 'calEvent', 'calEventText',
  ];
  assert.equal(retired.length, 17);
  for (const key of retired) {
    assert.ok(!(key in sheet), `${key}: retired key must not resurface`);
  }
});

test('Phase A regression: ThemeProvider switching still drives migrated components after the gx split', () => {
  const React = req('react') as typeof ReactNS;
  const { act } = req('react-test-renderer') as typeof TestRendererNS;
  const { themes, withAlpha } = req('@oryx/design-system') as typeof DesignSystemNS;
  const { EpistemicTypeBadge } = req(
    '../modules/verification/components/EpistemicTypeBadge',
  ) as typeof BadgeNS;
  const washes: Record<Mode, string[]> = { dark: [], light: [] };
  for (const mode of ['dark', 'light'] as const) {
    const tree = renderInMode(mode, React.createElement(EpistemicTypeBadge, { type: 'speculation' }));
    washes[mode] = colorsOf(tree);
    assert.ok(
      washes[mode].includes(withAlpha(themes[mode].colors.text.tertiary, 0.15)),
      `${mode}: the Phase A mechanism still resolves this mode's tokens`,
    );
    act(() => tree.unmount());
  }
  assert.notDeepEqual(washes.dark, washes.light, 'the switch still changes what renders');
});
