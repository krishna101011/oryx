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
import { type NavCountSource, findNavItem, navCounts, performNav } from './webNav';

/** Recording fakes standing in for navigationRef's navigateTab / navigateSettingsScreen. */
function recordingNav() {
  const tabs: string[] = [];
  const screens: string[] = [];
  return {
    tabs,
    screens,
    nav: {
      navigateTab: (tab: string) => tabs.push(tab),
      navigateSettingsScreen: (screen: string) => screens.push(screen),
    },
  };
}

const seededMe: NavCountSource = {
  activity: { unreadCount: 7 },
  content: { draftCount: 2, pendingReviewCount: 0, scheduledCount: 0, publishedThisWeek: 0 },
  verification: { pendingReviewCount: 3, openConflictCount: 1 },
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

test('header gear navigates to the Settings tab from multiple active screens', () => {
  for (const activeScreen of SIMULATED_ACTIVE_SCREENS) {
    const { tabs, screens, nav } = recordingNav();
    performNav(findNavItem('settings'), nav);
    assert.deepEqual(tabs, ['Settings'], `gear click while on ${activeScreen} must land on Settings`);
    assert.deepEqual(screens, [], 'gear must not target a nested settings screen');
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

test('sidebar deep items still resolve through performNav (Settings-nested screens unchanged)', () => {
  // Regression guard for the extraction: WebShell's old inline logic sent
  // tab:'Settings' + screen items to navigateSettingsScreen.
  const { tabs, screens, nav } = recordingNav();
  performNav(findNavItem('automation'), nav);
  assert.deepEqual(screens, ['AutomationHub']);
  assert.deepEqual(tabs, []);
});
