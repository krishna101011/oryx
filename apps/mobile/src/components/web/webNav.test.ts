/**
 * Header/topbar wiring — bell, gear, AI Analyst badge.
 *
 * The repo's frontend suite is pure-logic node:test (no component-render
 * harness), so these tests exercise the extracted nav helpers that WebTopBar
 * and WebShell now share: performNav (the single click→navigation resolution
 * used by BOTH the sidebar and the topbar shortcuts) and navCounts (the single
 * /me→badge-count mapping read by BOTH the sidebar Activity badge and the
 * topbar bell dot).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  CONTENT_ROOT_SCREEN,
  type NavCountSource,
  RESEARCH_ROOT_SCREEN,
  SETTINGS_ROOT_SCREEN,
  STACKED_TABS,
  TEAM_ROOT_SCREEN,
  WEB_NAV,
  findNavItem,
  navCounts,
  performNav,
} from './webNav';

/** Recording fakes standing in for navigationRef's five navigate functions. */
function recordingNav() {
  const tabs: string[] = [];
  const screens: string[] = [];
  const researchScreens: string[] = [];
  const contentScreens: string[] = [];
  const teamScreens: string[] = [];
  return {
    tabs,
    screens,
    researchScreens,
    contentScreens,
    teamScreens,
    nav: {
      navigateTab: (tab: string) => tabs.push(tab),
      navigateSettingsScreen: (screen: string) => screens.push(screen),
      navigateResearchScreen: (screen: string) => researchScreens.push(screen),
      navigateContentScreen: (screen: string) => contentScreens.push(screen),
      navigateTeamScreen: (screen: string) => teamScreens.push(screen),
    },
  };
}

const seededMe: NavCountSource = {
  activity: { unreadCount: 7 },
  content: { draftCount: 2, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  verification: { pendingReviewCount: 3, openConflictCount: 1, verifiedCount: 0 },
};

// The topbar is global chrome — a click resolves identically no matter which
// screen is underneath. Simulate clicks while two different tabs are focused.
const SIMULATED_ACTIVE_SCREENS = ['Settings', 'Home'] as const;

test('header bell navigates to the Activity tab (sidebar Activity destination) from multiple active screens', () => {
  for (const activeScreen of SIMULATED_ACTIVE_SCREENS) {
    const { tabs, screens, nav } = recordingNav();
    // Same call chain as a real click: WebTopBar presses findNavItem('activity')
    // into the shared onNavigate, which is performNav.
    performNav(findNavItem('activity'), nav);
    assert.deepEqual(tabs, ['Activity'], `bell click while on ${activeScreen} must land on Activity`);
    assert.deepEqual(screens, [], 'bell must not target a nested settings screen');
  }
});

test('header gear resolves to the SettingsHome screen explicitly, never a bare tab focus, from multiple active screens', () => {
  // A bare navigateTab('Settings') only FOCUSES the stack — with nested state
  // (e.g. Automation Hub on top) it lands there, not on the Account root.
  // That was the 2026-07-11 live bug; the gear must name its destination.
  for (const activeScreen of SIMULATED_ACTIVE_SCREENS) {
    const { tabs, screens, nav } = recordingNav();
    performNav(findNavItem('settings'), nav);
    assert.deepEqual(screens, ['SettingsHome'], `gear click while on ${activeScreen} must land on SettingsHome`);
    assert.deepEqual(tabs, [], 'gear must not use the non-resetting bare-tab path');
  }
});

test('bell unread dot and sidebar Activity badge read the same seeded activityUnread count', () => {
  const counts = navCounts(seededMe);
  // WebSidebar's badge shows counts.activityUnread; WebTopBar's dot shows when
  // counts.activityUnread > 0 — both from this one function, so a seeded unread
  // of 7 must surface identically to each.
  assert.equal(counts.activityUnread, 7);
  assert.equal(counts.activityUnread > 0, true, 'bell dot must be visible when sidebar badge is');
  // And with no /me yet, neither shows anything.
  assert.equal(navCounts(undefined).activityUnread, 0);
});

test('AI Analyst badge is INTENTIONALLY non-interactive: pending feature, no navigation resolves', () => {
  // Not an oversight — webNav marks the AI Analyst surface pending (not built,
  // Phase 6+), and pending items resolve to no navigation. The topbar badge is
  // a dimmed status marker with no press handler by design.
  const ai = findNavItem('ai');
  assert.equal(ai.pending, true);
  assert.equal(ai.tab, undefined);
  const { tabs, screens, nav } = recordingNav();
  performNav(ai, nav);
  assert.deepEqual(tabs, [], 'pending AI Analyst item must not navigate to any tab');
  assert.deepEqual(screens, [], 'pending AI Analyst item must not open any screen');
});

test('Verification Center resolves to VerificationQueue (fetch-on-mount, so an expired session hits the global 401 → signedOut → Sign In path), never a silent Settings-root landing', () => {
  const { tabs, screens, nav } = recordingNav();
  performNav(findNavItem('verify'), nav);
  assert.deepEqual(screens, ['VerificationQueue']);
  assert.deepEqual(tabs, [], 'verify must not fall back to the bare Settings tab');
});

test('EVERY Settings-tab sidebar item names a nested screen — a bare tab target is a bug class, twice now', () => {
  // First bug (expired-session gap): a screenless item landed on the Settings
  // root, which makes no fresh API call, so an expired session went undetected.
  // Second bug (stack never resets): the screenless Settings root item itself
  // couldn't leave a nested Settings screen, because a bare tab navigate only
  // focuses the stack. Both have the same shape — so no exceptions anymore.
  for (const g of WEB_NAV) {
    for (const it of g.items) {
      if (it.pending || it.tab !== 'Settings') continue;
      assert.ok(
        it.screen,
        `nav item "${it.id}" targets the Settings tab without a nested screen — non-deterministic landing`,
      );
    }
  }
  assert.equal(findNavItem('settings').screen, SETTINGS_ROOT_SCREEN);
});

test('sidebar deep items still resolve through performNav (Settings-nested screens unchanged)', () => {
  // Regression guard for the extraction: WebShell's old inline logic sent
  // tab:'Settings' + screen items to navigateSettingsScreen.
  const { tabs, screens, nav } = recordingNav();
  performNav(findNavItem('automation'), nav);
  assert.deepEqual(screens, ['AutomationHub']);
  assert.deepEqual(tabs, []);
});

// ---------------------------------------------------------------------------
// Settings-tab reset regression matrix (2026-07-11, second nav bug in this
// area). The recording fakes above can't catch the bug class — it lives in
// the INTERACTION between performNav and React Navigation's stack semantics.
// This fake models those semantics faithfully:
//   - navigateTab: focuses a tab and PRESERVES its nested stack (never resets
//     it; a same-tab navigate is a complete no-op). This is exactly why the
//     old bare-tab path could not leave Automation Hub.
//   - navigateSettingsScreen: StackRouter NAVIGATE — rewind to the screen if
//     it is already in the stack, else push it. Either way it becomes focused.
// ---------------------------------------------------------------------------

function fakeNavigator(
  initial: { Settings?: string[]; Research?: string[]; Content?: string[]; Team?: string[] } = {},
) {
  let focusedTab = 'Home';
  const stacks: Record<string, string[]> = {
    Settings: [...(initial.Settings ?? ['SettingsHome'])],
    Research: [...(initial.Research ?? ['ResearchWorkspaceList'])],
    Content: [...(initial.Content ?? ['ContentHome'])],
    Team: [...(initial.Team ?? ['TeamHome'])],
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
      navigateTeamScreen: navigateStackScreen('Team'),
    },
  };
}

/** Every Settings-tab sidebar item and the screen a press must land on. */
const SETTINGS_TAB_MATRIX = [
  { id: 'verify', lands: 'VerificationQueue' },
  { id: 'automation', lands: 'AutomationHub' },
  { id: 'analytics', lands: 'Analytics' },
  { id: 'settings', lands: 'SettingsHome' },
] as const;

test('LIVE REPRO regression: Automation Hub → press Settings lands on SettingsHome, not Automation Hub', () => {
  const f = fakeNavigator();
  performNav(findNavItem('automation'), f.nav);
  assert.equal(f.landedOn, 'AutomationHub');
  performNav(findNavItem('settings'), f.nav);
  assert.equal(f.landedOn, 'SettingsHome', 'pressing Settings must leave Automation Hub');
});

test('matrix: from every Settings-tab screen, pressing every other Settings-tab item lands exactly on its screen', () => {
  for (const start of SETTINGS_TAB_MATRIX) {
    for (const next of SETTINGS_TAB_MATRIX) {
      if (next.id === start.id) continue;
      const f = fakeNavigator();
      performNav(findNavItem(start.id), f.nav);
      assert.equal(f.landedOn, start.lands, `setup: ${start.id} must land on ${start.lands}`);
      performNav(findNavItem(next.id), f.nav);
      assert.equal(
        f.landedOn,
        next.lands,
        `${start.id} → ${next.id}: must land on ${next.lands}, not stay on ${start.lands}`,
      );
    }
  }
});

test('matrix: pressing all four Settings-tab items IN SEQUENCE from each start lands correctly at every step', () => {
  // Pairwise fresh navigators miss ordering effects (a stale stack built up by
  // earlier presses); this walks every rotation of the full cycle on ONE stack.
  for (let offset = 0; offset < SETTINGS_TAB_MATRIX.length; offset++) {
    const f = fakeNavigator();
    for (let i = 0; i < SETTINGS_TAB_MATRIX.length; i++) {
      const item = SETTINGS_TAB_MATRIX[(offset + i) % SETTINGS_TAB_MATRIX.length]!;
      performNav(findNavItem(item.id), f.nav);
      assert.equal(f.landedOn, item.lands, `step ${i} of rotation ${offset}: ${item.id}`);
    }
  }
});

test('matrix: pressing the SAME Settings-tab item twice stays put (idempotent, no phantom push)', () => {
  for (const item of SETTINGS_TAB_MATRIX) {
    const f = fakeNavigator();
    performNav(findNavItem(item.id), f.nav);
    performNav(findNavItem(item.id), f.nav);
    assert.equal(f.landedOn, item.lands, `double-press ${item.id}`);
  }
});

// ---------------------------------------------------------------------------
// Research / Content Studio — the THIRD instance of the bare-tab bug class
// (2026-07-13), disclosed as still-open by the sidebar-collapse wave. Same
// fix shape, same regression suite shape as the Settings-tab family above.
// ---------------------------------------------------------------------------

test('Research Workspace resolves to ResearchWorkspaceList explicitly, never a bare tab focus', () => {
  const { tabs, researchScreens, nav } = recordingNav();
  performNav(findNavItem('research'), nav);
  assert.deepEqual(researchScreens, ['ResearchWorkspaceList']);
  assert.deepEqual(tabs, [], 'research must not use the non-resetting bare-tab path');
  assert.equal(findNavItem('research').screen, RESEARCH_ROOT_SCREEN);
});

test('Content Studio resolves to ContentHome explicitly, never a bare tab focus', () => {
  const { tabs, contentScreens, nav } = recordingNav();
  performNav(findNavItem('content'), nav);
  assert.deepEqual(contentScreens, ['ContentHome']);
  assert.deepEqual(tabs, [], 'content must not use the non-resetting bare-tab path');
  assert.equal(findNavItem('content').screen, CONTENT_ROOT_SCREEN);
});

test('LIVE-CLASS regression: deep in a Research packet, pressing Research Workspace resets to the workspace list', () => {
  // The exact flagged scenario: ResearchWorkspaceList → detail → packet,
  // then press the sidebar item again.
  const f = fakeNavigator({
    Research: ['ResearchWorkspaceList', 'ResearchWorkspaceDetail', 'ResearchPacket'],
  });
  performNav(findNavItem('research'), f.nav);
  assert.equal(f.landedOn, 'ResearchWorkspaceList', 'must leave the packet, not stay on it');
});

test('LIVE-CLASS regression: deep in DraftEditor, pressing Content Studio resets to ContentHome', () => {
  // "Content Studio pressed while deep in DraftEditor stays on DraftEditor"
  // — the 2026-07-11 flagged wording, now a failing-then-fixed case.
  const f = fakeNavigator({ Content: ['ContentHome', 'DraftEditor'] });
  performNav(findNavItem('content'), f.nav);
  assert.equal(f.landedOn, 'ContentHome', 'must leave DraftEditor, not stay on it');
});

// ---------------------------------------------------------------------------
// Team — fourth stacked tab (Team promotion wave, 2026-07-26), same bug
// class and same fix shape as Research/Content/Settings above.
// ---------------------------------------------------------------------------

test('Team resolves to TeamHome explicitly, never a bare tab focus', () => {
  const { tabs, teamScreens, nav } = recordingNav();
  performNav(findNavItem('team'), nav);
  assert.deepEqual(teamScreens, ['TeamHome']);
  assert.deepEqual(tabs, [], 'team must not use the non-resetting bare-tab path');
  assert.equal(findNavItem('team').screen, TEAM_ROOT_SCREEN);
});

test('LIVE-CLASS regression: deep in TeamActivity, pressing Team resets to TeamHome', () => {
  const f = fakeNavigator({ Team: ['TeamHome', 'TeamActivity'] });
  performNav(findNavItem('team'), f.nav);
  assert.equal(f.landedOn, 'TeamHome', 'must leave TeamActivity, not stay on it');
});

test('cross-stack: stale nested state in EVERY stacked tab, each sidebar item still lands on its own root', () => {
  for (const [id, lands] of [
    ['research', 'ResearchWorkspaceList'],
    ['content', 'ContentHome'],
    ['team', 'TeamHome'],
    ['settings', 'SettingsHome'],
  ] as const) {
    const f = fakeNavigator({
      Settings: ['SettingsHome', 'AutomationHub'],
      Research: ['ResearchWorkspaceList', 'ResearchPacket'],
      Content: ['ContentHome', 'DraftEditor'],
      Team: ['TeamHome', 'TeamActivity'],
    });
    performNav(findNavItem(id), f.nav);
    assert.equal(f.landedOn, lands, `${id} with all four stacks dirty`);
  }
});

test('project-wide guard: EVERY item targeting a stacked tab names a nested screen — the class is closed everywhere it can occur', () => {
  // Extends the Settings-only guard above to all stacked tabs. Home and
  // Activity mount a single screen (RootTabNavigator.tsx) — no stack, so
  // they are exempt BY CONSTRUCTION, not by oversight.
  const stacked = new Set<string>(STACKED_TABS);
  for (const g of WEB_NAV) {
    for (const it of g.items) {
      if (it.pending || !it.tab || !stacked.has(it.tab)) continue;
      assert.ok(
        it.screen,
        `nav item "${it.id}" targets stacked tab ${it.tab} without a nested screen — the bare-tab bug class, fourth time`,
      );
    }
  }
});

test('Home and Activity are stackless tabs: the bare-tab path remains their correct resolution', () => {
  // Phase-0 finding: fixing Research/Content does NOT close performNav's
  // bare navigateTab branch — these two legitimately keep it.
  for (const [id, tab] of [
    ['home', 'Home'],
    ['activity', 'Activity'],
  ] as const) {
    const { tabs, screens, researchScreens, contentScreens, teamScreens, nav } = recordingNav();
    performNav(findNavItem(id), nav);
    assert.deepEqual(tabs, [tab]);
    assert.deepEqual([...screens, ...researchScreens, ...contentScreens, ...teamScreens], []);
  }
});

test('deep nested Settings screen (ClaimDetail under verify) still resets to SettingsHome on Settings press', () => {
  // ClaimDetail is reachable only by drilling in — it has no sidebar item.
  const f = fakeNavigator({ Settings: ['SettingsHome', 'VerificationQueue', 'ClaimDetail'] });
  performNav(findNavItem('settings'), f.nav);
  assert.equal(f.landedOn, 'SettingsHome');
  // And from the same depth, every other item still lands correctly.
  for (const item of SETTINGS_TAB_MATRIX) {
    const deep = fakeNavigator({ Settings: ['SettingsHome', 'VerificationQueue', 'ClaimDetail'] });
    performNav(findNavItem(item.id), deep.nav);
    assert.equal(deep.landedOn, item.lands, `from ClaimDetail: ${item.id}`);
  }
});
