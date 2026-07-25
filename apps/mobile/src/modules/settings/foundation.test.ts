/**
 * Settings design-foundation wave (ST-1..ST-4, 2026-07-20) — the last screen
 * in the design-foundation series. Source scans follow the established RW/AH
 * pattern (no component-render harness needed for these anatomy checks).
 *
 * Phase 0 correction: no ST-1..ST-6 recon document exists anywhere in the
 * repo, git history, or memory (checked before this wave started) — this
 * wave's Phase 0 is fresh recon against the real current code, not a
 * re-confirmation of a prior document. It also found that the "two-column
 * form grid" / "session table" / "source table" referenced in the task exist
 * ONLY in the aspirational design-reference mockup
 * (docs/design-reference/screens/settings.jsx — MFA, Audit log, trust tiers,
 * Billing, API tokens, Admin: none of these were ever built). The REAL built
 * Settings screens have no table/grid anywhere; every one is already a
 * single-column card/list anatomy. So this wave applies the foundation to
 * every real Settings screen rather than deferring a desktop table that does
 * not exist in code.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const read = (rel: string): string =>
  stripComments(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8'));

const MIGRATED_FILES = [
  './screens/SettingsHomeScreen.tsx',
  './components/SettingsRow.tsx',
  './screens/ActiveSessionsScreen.tsx',
  './sessions.ts',
];

// ---- token violation sweep --------------------------------------------------

test('token sweep: no hardcoded hex/rgba color or hardcoded borderRadius survives in the touched Settings files', () => {
  // SettingsRow.tsx and ActiveSessionsScreen.tsx both carried
  // `borderRadius: 8` on the 36x36 icon well (on-scale for radius.xl, but
  // still a hardcoded literal rather than the token — the AH-4 precedent
  // rejects ANY numeric borderRadius literal, not just off-scale ones).
  for (const rel of MIGRATED_FILES) {
    const source = read(rel);
    assert.ok(!/rgba?\(/.test(source), `${rel}: no rgba()/rgb() literals`);
    assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(source), `${rel}: no hex literals`);
    assert.ok(!/borderRadius:\s*\d/.test(source), `${rel}: no hardcoded borderRadius literal`);
  }
});

test('the fixed icon wells route through the real radius token (radius.xl, the prior 8px value)', () => {
  for (const rel of ['./components/SettingsRow.tsx', './screens/ActiveSessionsScreen.tsx']) {
    const source = read(rel);
    assert.ok(source.includes('t.radius.xl'), `${rel}: icon well radius from the scale`);
  }
});

// ---- CardHeader / HairlineRowList anatomy -----------------------------------

test('SettingsHomeScreen groups every navigation-row section under CardHeader + HairlineRowList', () => {
  const screen = read('./screens/SettingsHomeScreen.tsx');
  for (const title of ['Profile', 'Plan', 'Security', 'Alerts', 'Automation', 'Sources', 'Verification']) {
    assert.ok(screen.includes(`<CardHeader title="${title}"`), `real CardHeader for ${title}`);
  }
  // 7 sections migrated to the row/list anatomy = 7 HairlineRowList groups
  // (billing wave, 2026-07-26, added the Plan section right after Profile).
  const hairlineCount = (screen.match(/<HairlineRowList>/g) ?? []).length;
  assert.equal(hairlineCount, 7, 'one HairlineRowList per migrated section');
});

test('SettingsRow no longer wraps itself in its own Card — it is a bare row for a parent HairlineRowList', () => {
  const row = read('./components/SettingsRow.tsx');
  assert.ok(!row.includes('Card'), 'no Card import or usage remains in the row itself');
});

test('ActiveSessionsScreen groups sessions under a real CardHeader with the pluralized device-count sub', () => {
  const screen = read('./screens/ActiveSessionsScreen.tsx');
  assert.ok(screen.includes('<CardHeader title="Sessions"'), 'real CardHeader');
  assert.ok(screen.includes('deviceCountSub'), 'header sub is the real, pluralized count');
  assert.ok(screen.includes('<HairlineRowList>'), 'session rows pack through HairlineRowList');
});

// ---- deliberate deferrals, pinned (RW-2/AN-3 precedent) --------------------

test('deferred honestly: Appearance, Alerts-preferences, and Trusted Sources keep their ChoiceTile anatomy', () => {
  // ChoiceTile IS a Card (selection border/dot are the card's own chrome) and
  // is shared with the onboarding module outside this wave's scope. Wrapping
  // its rows in HairlineRowList would strip the selected-state border that
  // makes the picker legible, and editing ChoiceTile itself would touch a
  // screen outside Settings. So these three ChoiceTile-based sections keep
  // their current (already Card + real-typography + token-color-compliant)
  // anatomy rather than a forced CardHeader/HairlineRowList retrofit.
  //
  // TrustedSourcesScreen no longer inlines ChoiceTile directly (source-catalog
  // picker rebuild, 2026-07-23): it composes the shared
  // modules/intake/components/CatalogSourcePicker, which itself renders every
  // tile via ChoiceTile — so the anatomy check follows the real render chain
  // instead of a literal string match on the screen file.
  const home = read('./screens/SettingsHomeScreen.tsx');
  assert.ok(home.includes('ChoiceTile'), 'Appearance still renders via ChoiceTile');

  const alerts = read('./screens/AlertsSettingsScreen.tsx');
  assert.ok(alerts.includes('ChoiceTile'), 'Alerts-preferences still renders via ChoiceTile');
  assert.ok(!alerts.includes('HairlineRowList'), 'Alerts-preferences: not force-migrated this wave');

  const trustedSources = read('./screens/TrustedSourcesScreen.tsx');
  assert.ok(
    trustedSources.includes('CatalogSourcePicker'),
    'Trusted Sources renders through the shared catalog picker',
  );
  assert.ok(
    !trustedSources.includes('HairlineRowList'),
    'Trusted Sources: not force-migrated this wave',
  );
  const picker = read('../intake/components/CatalogSourcePicker.tsx');
  assert.ok(picker.includes('ChoiceTile'), 'the shared picker still renders tiles via ChoiceTile');
  assert.ok(!picker.includes('HairlineRowList'), 'the shared picker is not force-migrated this wave');
});

test('deferred honestly: ProfileEdit and ChangePassword stay plain forms — no row/list anatomy exists to migrate', () => {
  for (const rel of ['./screens/ProfileEditScreen.tsx', './screens/ChangePasswordScreen.tsx']) {
    const source = read(rel);
    assert.ok(!source.includes('CardHeader'), `${rel}: no row/list section, so no CardHeader`);
    assert.ok(!/rgba?\(/.test(source) && !/#[0-9a-fA-F]{3,8}\b/.test(source), `${rel}: token-clean`);
  }
});

test('ST-5 fixed: no Settings row uses the surface-only teal accent as an icon glyph color', () => {
  // Live-verification bug (2026-07-20): the Verification row passed
  // accent="teal" to SettingsRow -> Icon color="teal", which resolves to
  // colors.ts's accent.teal — documented SURFACE-ONLY (fills/washes; 1.49:1
  // contrast vs bg in dark, a near-white wash in light). The icon rendered
  // faintly in dark mode by coincidence and was fully invisible in light
  // mode (light accent.teal = #E3EFFA, a pale wash, on a near-white icon
  // well). Confirmed this was the ONLY accent="teal"/color="teal" icon-glyph
  // usage anywhere in the mobile app (repo-wide grep) — fixed by swapping to
  // "coral" (a real glyph-safe accent, same family already used elsewhere in
  // this screen).
  const home = read('./screens/SettingsHomeScreen.tsx');
  assert.ok(!/accent="teal"/.test(home), 'Verification row no longer uses the surface-only teal accent');
});

test('out of scope, not part of this Settings module: AutomationHub/Analytics/IntakeHome/VerificationQueue rows only link out', () => {
  // These four rows in SettingsHomeScreen navigate to screens owned by other
  // modules (automation/, analytics/, intake/, verification/) that already
  // had their own dedicated design-foundation waves (AH-1..AH-4, AN-2/AN-3)
  // or remain that module's own future wave (intake, verification). This
  // wave only styles the LINK ROW inside Settings, never the destination
  // screen — confirmed no automation/analytics/intake/verification screen
  // file was touched.
  const home = read('./screens/SettingsHomeScreen.tsx');
  for (const target of ['AutomationHub', 'Analytics', 'IntakeHome', 'VerificationQueue']) {
    assert.ok(home.includes(`navigate('${target}'`), `${target} row still links out, unchanged`);
  }
});
