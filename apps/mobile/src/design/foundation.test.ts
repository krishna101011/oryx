/* eslint-disable no-restricted-syntax --
 * The inline-hex ban keeps colors flowing through tokens; here the hexes ARE
 * the expected values the tokens are pinned against. Deriving them from the
 * tokens would make every assertion a tautology. */
/**
 * Design-foundation wave tests (2026-07-12) — token decisions, typography
 * adoption, and Card density. Token behavior is tested directly against
 * @oryx/design-system/tokens (pure TS, safe under node:test). Call-site and
 * component claims use the repo's source-scan precedent (see stats.test.ts's
 * badge-removal test): no component-render harness exists, so the honest
 * available proof is that the source contains/lacks the exact variants.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  channelColors,
  gradients,
  typography,
  withAlpha,
} from '@oryx/design-system/tokens';

const read = (relToRepoRoot: string): string =>
  readFileSync(
    fileURLToPath(new URL(`../../../../${relToRepoRoot}`, import.meta.url)),
    'utf8',
  );

// ---- Phase 1.2 — withAlpha generalizes tealAlpha ---------------------------

test('withAlpha converts #RRGGBB tokens into the exact rgba() channel triplet', () => {
  assert.equal(withAlpha('#08314A', 0.3), 'rgba(8,49,74,0.3)');
  assert.equal(withAlpha('#FF6719', 0.5), 'rgba(255,103,25,0.5)');
  assert.equal(withAlpha('#0a66c2', 1), 'rgba(10,102,194,1)');
});

test('withAlpha reproduces every wash the retired tealAlpha helper produced', () => {
  // The old helper was rgba(8,49,74,a). Its real call-site alphas: chip washes
  // 0.06/0.3, ws-icon 0.12, tealGlow 0.15, Card hover 0.18/0.22.
  for (const a of [0.06, 0.12, 0.15, 0.18, 0.22, 0.3]) {
    assert.equal(withAlpha('#08314A', a), `rgba(8,49,74,${a})`);
  }
});

test('withAlpha rejects non-#RRGGBB inputs instead of emitting broken colors', () => {
  for (const bad of ['rgba(0,0,0,1)', '#FFF', '#08314A80', 'tomato', '']) {
    assert.throws(() => withAlpha(bad, 0.5), /expects a #RRGGBB/);
  }
});

test('the teal-specific alpha helper is fully retired from the design system', () => {
  for (const file of [
    'packages/design-system/src/tokens/colors.ts',
    'packages/design-system/src/styles/genspark.ts',
    'packages/design-system/src/components/Card.tsx',
  ]) {
    assert.ok(
      !read(file).includes('tealAlpha('),
      `${file} must not call the retired tealAlpha helper`,
    );
  }
  assert.ok(
    !read('packages/design-system/src/tokens/colors.ts').includes(
      'export const tealAlpha',
    ),
    'the tealAlpha export itself must be gone',
  );
});

// ---- Phase 1.1 — channel attribution tokens --------------------------------

test('channel attribution tokens hold exactly the two reference brand values', () => {
  assert.deepEqual(channelColors, {
    substack: '#FF6719',
    linkedin: '#0a66c2',
  });
});

// ---- Phase 1.3 — confidence dial reuses gradients.accent -------------------

test('no confidence-dial gradient was added — the dial decision reuses gradients.accent', () => {
  assert.deepEqual(Object.keys(gradients).sort(), [
    'accent',
    'accentSoft',
    'avatar',
    'meterNeg',
    'meterTeal',
    'sidebar',
  ]);
  assert.equal(gradients.accent.from, '#5B5BF5');
  assert.equal(gradients.accent.to, '#8B5CF6');
});

// ---- Phase 2 — typography adoption -----------------------------------------

test('cardTitle carries the reference uppercase transform in the token itself', () => {
  assert.equal(typography.cardTitle.textTransform, 'uppercase');
  assert.equal(typography.cardTitle.fontSize, 11.5);
});

test('recon-cited screen titles use pageTitle, and the oversized display alias is gone from them', () => {
  const screens = [
    'apps/mobile/src/modules/verification/screens/VerificationQueueScreen.tsx',
    'apps/mobile/src/modules/research/screens/ResearchWorkspaceListScreen.tsx',
    'apps/mobile/src/modules/content/screens/ContentHomeScreen.tsx',
    'apps/mobile/src/modules/automation/screens/AutomationHubScreen.tsx',
    'apps/mobile/src/modules/analytics/screens/AnalyticsHomeScreen.tsx',
    'apps/mobile/src/modules/settings/screens/SettingsHomeScreen.tsx',
    'apps/mobile/src/modules/settings/screens/ProfileEditScreen.tsx',
    'apps/mobile/src/modules/settings/screens/ChangePasswordScreen.tsx',
    'apps/mobile/src/modules/settings/screens/ActiveSessionsScreen.tsx',
    'apps/mobile/src/modules/settings/screens/TrustedSourcesScreen.tsx',
    'apps/mobile/src/modules/settings/screens/AlertsSettingsScreen.tsx',
  ];
  for (const screen of screens) {
    const source = read(screen);
    assert.ok(
      source.includes('variant="pageTitle"'),
      `${screen} must title itself with pageTitle`,
    );
    assert.ok(
      !source.includes('variant="display"'),
      `${screen} must no longer use the display alias`,
    );
  }
});

test('Analytics stat values render in kpiVal mono, not the h1 alias', () => {
  const source = read(
    'apps/mobile/src/modules/analytics/screens/AnalyticsHomeScreen.tsx',
  );
  assert.equal(source.match(/variant="kpiVal"/g)?.length, 3);
  assert.ok(!source.includes('variant="h1"'));
});

test("Command Center's Today panel title uses the cardTitle variant", () => {
  const source = read(
    'apps/mobile/src/modules/dashboard/screens/DashboardScreen.tsx',
  );
  assert.ok(source.includes('variant="cardTitle"'));
  assert.ok(!source.includes('variant="h2"'));
});

// ---- Phase 3 — Card density + the two new primitives -----------------------

test('Card matches the reference density: 12px body padding, #1A2330 border, no shadow', () => {
  const source = read('packages/design-system/src/components/Card.tsx');
  assert.ok(source.includes('t.spacing[3]'), 'body padding must be spacing[3] = 12');
  assert.ok(
    source.includes('t.colors.border.default'),
    'card edge must use border.default (#1A2330), not the hairline',
  );
  assert.ok(!source.includes('spacing[5]'), 'the old 20px padding must be gone');
  assert.ok(
    !source.includes('shadowColor') && !source.includes('elevation:'),
    'cards are flat in the reference — the elevated drop shadow must be gone',
  );
});

test('the two reference primitives exist, follow their source rules, and are exported', () => {
  const header = read('packages/design-system/src/components/CardHeader.tsx');
  assert.ok(header.includes('variant="cardTitle"'), 'header title = cardTitle');
  assert.ok(
    header.includes('border.default'),
    'header strip border = --border, per .card-head',
  );
  const rows = read('packages/design-system/src/components/HairlineRowList.tsx');
  assert.ok(
    rows.includes('border.subtle'),
    'row separators = --hairline, per the in-card list pattern',
  );
  const barrel = read('packages/design-system/src/components/index.ts');
  assert.ok(barrel.includes("from './CardHeader'"));
  assert.ok(barrel.includes("from './HairlineRowList'"));
});
