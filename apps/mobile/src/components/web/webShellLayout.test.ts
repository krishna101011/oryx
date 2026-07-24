/**
 * Sidebar collapse wave (2026-07-13) — breakpoint math, drawer navigation,
 * and active-highlight mapping. Third real bug in the web-nav area, so the
 * two prior fixes (Settings-tab reset, Verification Center routing) are
 * regression-tested THROUGH the new collapsed path, not assumed to hold.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { findNavItem, performNav } from './webNav';
import {
  MIN_CONTENT_WIDTH,
  SIDEBAR_COLLAPSE_BREAKPOINT,
  SIDEBAR_WIDTH,
  activeNavIdFor,
  drawerNavigate,
  sidebarMode,
} from './webShellLayout';

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const shellSource = (): string =>
  stripComments(
    readFileSync(fileURLToPath(new URL('./WebShell.tsx', import.meta.url)), 'utf8'),
  );

// ---- breakpoint -------------------------------------------------------------

test('sidebar is expanded at the breakpoint and above, collapsed strictly below it', () => {
  assert.equal(sidebarMode(SIDEBAR_COLLAPSE_BREAKPOINT), 'expanded');
  assert.equal(sidebarMode(SIDEBAR_COLLAPSE_BREAKPOINT - 1), 'collapsed');
  // The two live-verified widths from the Command Center wave: 1440 kept the
  // full rail; a 390px window (~268px content) is exactly the crowding case.
  assert.equal(sidebarMode(1440), 'expanded');
  assert.equal(sidebarMode(390), 'collapsed');
});

test('the breakpoint is derived from real layout constants, not a guessed number', () => {
  // Sidebar: the gx `sidebar` key's width 232 (genspark.ts). Content floor: Command
  // Center's 2-up KPI wrap point — two 150px-floor tiles + the 12px gap
  // (DashboardScreen.tsx) inside Screen's 16px-per-side canonical padding.
  assert.equal(SIDEBAR_WIDTH, 232);
  assert.equal(MIN_CONTENT_WIDTH, 150 * 2 + 12 + 16 * 2);
  assert.equal(SIDEBAR_COLLAPSE_BREAKPOINT, SIDEBAR_WIDTH + MIN_CONTENT_WIDTH);
  assert.equal(SIDEBAR_COLLAPSE_BREAKPOINT, 576);
});

// ---- active-item highlight (drives BOTH expanded rail and collapsed drawer) --

test('activeNavIdFor maps every navigable tab and disambiguates the nested Settings surfaces', () => {
  assert.equal(activeNavIdFor('Home', 'DashboardScreen'), 'home');
  assert.equal(activeNavIdFor('Research', undefined), 'research');
  assert.equal(activeNavIdFor('Content', 'DraftEditor'), 'content');
  assert.equal(activeNavIdFor('Activity', undefined), 'activity');
  assert.equal(activeNavIdFor('Settings', 'SettingsHome'), 'settings');
  assert.equal(activeNavIdFor('Settings', 'VerificationQueue'), 'verify');
  assert.equal(activeNavIdFor('Settings', 'ClaimDetail'), 'verify');
  assert.equal(activeNavIdFor('Settings', 'AutomationHub'), 'automation');
  assert.equal(activeNavIdFor('Settings', 'Analytics'), 'analytics');
});

test('activeNavIdFor returns null for non-navigable state so the previous highlight is kept', () => {
  // The 2026-07-12 stale-highlight rule: never clobber the highlight on a
  // no-op state event (auth screens, mid-transition undefined route).
  assert.equal(activeNavIdFor(undefined, undefined), null);
  assert.equal(activeNavIdFor('SignIn', undefined), null);
});

test('both sidebar renders receive the SAME activeId state — the highlight cannot fork by viewport', () => {
  const source = shellSource();
  const renders = source.match(/<WebSidebar[^>]*activeId=\{activeId\}/g) ?? [];
  assert.equal(renders.length, 2, 'expanded rail + collapsed drawer, one shared activeId');
});

// ---- drawer navigation: same resolution, plus close ------------------------

/** The React-Navigation-faithful fake from webNav.test.ts (tab focus never
 * resets a nested stack; screen navigate rewinds-or-pushes in its own stack). */
function fakeNavigator(initial: { Settings?: string[]; Research?: string[]; Content?: string[] } = {}) {
  let focusedTab = 'Home';
  const stacks: Record<string, string[]> = {
    Settings: [...(initial.Settings ?? ['SettingsHome'])],
    Research: [...(initial.Research ?? ['ResearchWorkspaceList'])],
    Content: [...(initial.Content ?? ['ContentHome'])],
  };
  const navigateStackScreen = (tab: string) => (screen: string) => {
    focusedTab = tab;
    const stack = stacks[tab]!;
    const at = stack.indexOf(screen);
    stacks[tab] = at >= 0 ? stack.slice(0, at + 1) : [...stack, screen];
  };
  return {
    get landedOn(): string {
      const stack = stacks[focusedTab];
      return stack ? stack[stack.length - 1]! : focusedTab;
    },
    nav: {
      navigateTab: (tab: string) => {
        focusedTab = tab;
      },
      navigateSettingsScreen: navigateStackScreen('Settings'),
      navigateResearchScreen: navigateStackScreen('Research'),
      navigateContentScreen: navigateStackScreen('Content'),
    },
  };
}

/** Drawer harness: drawerNavigate wired to the REAL performNav, like WebShell. */
function drawerHarness(initial?: { Settings?: string[]; Research?: string[]; Content?: string[] }) {
  const f = fakeNavigator(initial);
  let open = true;
  return {
    f,
    get open() {
      return open;
    },
    press: (id: string) =>
      drawerNavigate(findNavItem(id), {
        close: () => {
          open = false;
        },
        perform: (item) => performNav(item, f.nav),
      }),
  };
}

test('a drawer press closes the drawer and resolves through the real performNav', () => {
  const h = drawerHarness();
  h.press('research');
  assert.equal(h.open, false, 'drawer must close on navigation');
  assert.equal(h.f.landedOn, 'ResearchWorkspaceList');
});

test('REGRESSION through the collapsed path: Research and Content Studio presses reset their own stacks to their home screens', () => {
  // The 2026-07-13 fix (third bare-tab instance) verified via the drawer too.
  for (const [id, lands] of [
    ['research', 'ResearchWorkspaceList'],
    ['content', 'ContentHome'],
  ] as const) {
    const h = drawerHarness({
      Research: ['ResearchWorkspaceList', 'ResearchWorkspaceDetail', 'ResearchPacket'],
      Content: ['ContentHome', 'DraftEditor'],
    });
    h.press(id);
    assert.equal(h.f.landedOn, lands, `drawer ${id} press with a dirty stack`);
    assert.equal(h.open, false, `drawer must close after ${id}`);
  }
});

test('REGRESSION through the collapsed path: Verification Center still lands on VerificationQueue, never a Settings-root landing', () => {
  const h = drawerHarness();
  h.press('verify');
  assert.equal(h.f.landedOn, 'VerificationQueue');
  assert.equal(h.open, false);
});

test('REGRESSION through the collapsed path: Settings press still resets a nested Settings stack to SettingsHome', () => {
  // The 2026-07-11 live bug shape, replayed via the drawer: drill to
  // Automation Hub, then press Settings from the collapsed nav.
  const h = drawerHarness();
  h.press('automation');
  assert.equal(h.f.landedOn, 'AutomationHub');
  h.press('settings');
  assert.equal(h.f.landedOn, 'SettingsHome', 'drawer Settings press must leave Automation Hub');
});

test('drawer presses on a deep nested stack (ClaimDetail) land every Settings-tab item correctly', () => {
  for (const [id, lands] of [
    ['verify', 'VerificationQueue'],
    ['automation', 'AutomationHub'],
    ['analytics', 'Analytics'],
    ['settings', 'SettingsHome'],
  ] as const) {
    const h = drawerHarness({ Settings: ['SettingsHome', 'VerificationQueue', 'ClaimDetail'] });
    h.press(id);
    assert.equal(h.f.landedOn, lands, `from ClaimDetail via drawer: ${id}`);
    assert.equal(h.open, false, `drawer must close after ${id}`);
  }
});

// ---- shell anatomy (source-scan; no component-render harness exists) --------

test('collapsed nav is an overlay, not push-content: absolute backdrop, no static sidebar', () => {
  const source = shellSource();
  assert.ok(
    source.includes('{!collapsed ? <WebSidebar'),
    'the static 232px rail must not render while collapsed',
  );
  assert.ok(
    /drawerBackdrop:\s*\{[^}]*position: 'absolute'/.test(source),
    'the drawer floats above content instead of narrowing it',
  );
  assert.ok(
    source.includes('onOpenNav={collapsed ?'),
    'the hamburger trigger exists only in the collapsed state',
  );
});
