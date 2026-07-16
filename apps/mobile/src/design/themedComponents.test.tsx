/* eslint-disable no-restricted-syntax --
 * The inline-hex ban keeps colors flowing through tokens; here the hexes ARE
 * the expected values the tokens are pinned against (foundation.test.ts
 * precedent). */
/**
 * Theming Phase A — rendered both-mode proof: the REAL migrated verification
 * components mount under ThemeProvider with each theme and resolve their
 * migrated washes/tracks to that mode's tokens (no residue of the old
 * rgba(127,127,127,…)/rgba(239,68,68,…) literals in either mode). Also hosts
 * the gx deferral regression (gx needs the react-native shims).
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

test('gx static sheet is unaffected by this wave (Phase B deferral — still the dark values)', () => {
  const { gx } = req('@oryx/design-system') as typeof DesignSystemNS;
  assert.equal((gx.card as { backgroundColor?: string }).backgroundColor, '#0A0E14');
  assert.equal((gx.card as { borderColor?: string }).borderColor, '#1A2330');
  assert.equal((gx.topbar as { backgroundColor?: string }).backgroundColor, '#05070A');
  assert.equal((gx.navBadge as { backgroundColor?: string }).backgroundColor, '#161D28');
});
