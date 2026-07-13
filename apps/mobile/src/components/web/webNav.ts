import type { GensparkIconName } from '@oryx/design-system';
import type { MeResponse } from '@oryx/shared-types';

/**
 * Web sidebar information architecture — the NAV group/label/icon STRUCTURE is
 * ported verbatim from docs/design-reference/data.jsx (this is design, not
 * placeholder data). What is NOT ported: the fake numeric badges (42/7/3/NEW)
 * — those were demo data. Items that map to a real, built tab carry a `tab`;
 * everything else is `pending: true` (Phase 6+ surfaces) and renders dimmed and
 * non-interactive rather than as a fake live screen.
 */
export type WebNavTab = 'Home' | 'Research' | 'Content' | 'Activity' | 'Settings';

export interface WebNavItem {
  id: string;
  label: string;
  icon: GensparkIconName;
  tab?: WebNavTab;
  /** A nested screen inside the tab's stack (e.g. Settings → AutomationHub). */
  screen?: string;
  pending?: boolean;
  /** Which real /me count (if any) drives a badge. No fake numbers. */
  countKey?: 'verifyPending' | 'contentDrafts' | 'activityUnread';
}

export interface WebNavGroup {
  group: string;
  items: WebNavItem[];
}

export const WEB_NAV: WebNavGroup[] = [
  {
    group: 'INTELLIGENCE',
    items: [
      { id: 'home', label: 'Command Center', icon: 'Home', tab: 'Home', countKey: 'activityUnread' },
      { id: 'news', label: 'News Intelligence', icon: 'News', pending: true },
      // screen is REQUIRED here: without it the item lands on the Settings
      // root, which fetches nothing — so an expired session is never detected
      // (no 401 → no signedOut → no Sign In redirect). VerificationQueue
      // fetches on mount, putting this item on the same expiry path as the
      // rest of the app. WebShell's VERIFY_SCREENS highlight map also expects
      // this destination.
      { id: 'verify', label: 'Verification Center', icon: 'Shield', tab: 'Settings', screen: 'VerificationQueue', countKey: 'verifyPending' },
    ],
  },
  {
    group: 'RESEARCH',
    items: [
      // screen is REQUIRED (third instance of the bare-tab bug class,
      // 2026-07-13): pressed while deep in a packet, a bare tab navigate
      // stayed on the packet. Same fix shape as the Settings-tab family.
      { id: 'research', label: 'Research Workspace', icon: 'Beaker', tab: 'Research', screen: 'ResearchWorkspaceList' },
      { id: 'ai', label: 'AI Analyst', icon: 'Sparkles', pending: true },
    ],
  },
  {
    group: 'MARKETS',
    items: [
      { id: 'technical', label: 'Technical Analysis', icon: 'Chart', pending: true },
      { id: 'terminal', label: 'Markets Terminal', icon: 'Globe', pending: true },
      { id: 'opps', label: 'Opportunities', icon: 'Target', pending: true },
    ],
  },
  {
    group: 'PUBLISHING',
    items: [
      // screen REQUIRED — same bug class as 'research' above (DraftEditor
      // pressed-Content-Studio-stays-put was the flagged 2026-07-11 latent).
      { id: 'content', label: 'Content Studio', icon: 'Pen', tab: 'Content', screen: 'ContentHome', countKey: 'contentDrafts' },
      { id: 'publish', label: 'Publishing Center', icon: 'Send', pending: true },
    ],
  },
  {
    group: 'OPERATIONS',
    items: [
      { id: 'automation', label: 'Automation Hub', icon: 'Zap', tab: 'Settings', screen: 'AutomationHub' },
      { id: 'analytics', label: 'Analytics', icon: 'Bar', tab: 'Settings', screen: 'Analytics' },
      { id: 'intake', label: 'Intake Engine', icon: 'Inbox', pending: true },
    ],
  },
  {
    group: 'LEARN',
    items: [{ id: 'academy', label: 'Academy', icon: 'Book', pending: true }],
  },
  {
    group: 'SYSTEM',
    items: [
      { id: 'activity', label: 'Activity', icon: 'Bell', tab: 'Activity', countKey: 'activityUnread' },
      // screen is REQUIRED here too (second real bug in this area, 2026-07-11):
      // a bare tab navigate can only FOCUS the Settings stack — it never resets
      // nested state, so clicking "Settings" while on Automation Hub/Analytics/
      // Verification stayed on that screen. Naming the root screen makes the
      // press an explicit destination, like every other Settings-tab item.
      { id: 'settings', label: 'Settings', icon: 'Cog', tab: 'Settings', screen: 'SettingsHome' },
    ],
  },
];

/** The /me slices that carry badge counts (full MeResponse satisfies this). */
export type NavCountSource = Pick<MeResponse, 'activity' | 'content' | 'verification'>;

/**
 * The one place real /me counts become nav-badge numbers. Both the sidebar
 * (numeric badges) and the topbar bell (unread dot) read from here, so the two
 * can never disagree about unread state.
 */
export function navCounts(me?: NavCountSource): Record<NonNullable<WebNavItem['countKey']>, number> {
  return {
    verifyPending: me?.verification.pendingReviewCount ?? 0,
    contentDrafts: me?.content.draftCount ?? 0,
    activityUnread: me?.activity.unreadCount ?? 0,
  };
}

/** Look up a nav item by id. WEB_NAV is static, so a missing id is a code bug. */
export function findNavItem(id: string): WebNavItem {
  for (const g of WEB_NAV) {
    const it = g.items.find((i) => i.id === id);
    if (it) return it;
  }
  throw new Error(`webNav: no nav item with id "${id}"`);
}

/** Where a Settings-tab item without an explicit screen must land. */
export const SETTINGS_ROOT_SCREEN = 'SettingsHome';
/** Same deterministic-root rule for the other two STACKED tabs (2026-07-13). */
export const RESEARCH_ROOT_SCREEN = 'ResearchWorkspaceList';
export const CONTENT_ROOT_SCREEN = 'ContentHome';

/**
 * The tabs that mount a nested stack — the only tabs where a bare tab-level
 * navigate can strand the user on stale nested state. Home and Activity mount
 * a single screen directly (RootTabNavigator), so the bare-tab path is
 * CORRECT for them: there is no stack to reset.
 */
export const STACKED_TABS = ['Settings', 'Research', 'Content'] as const;

/**
 * Resolve a nav item to real navigation. Extracted from WebShell so the topbar
 * shortcuts (bell → 'activity', gear → 'settings') go through the exact same
 * resolution as a sidebar click, and so tests can inject recording fakes.
 * Pending items resolve to nothing — they have no built destination.
 *
 * Stacked-tab items (Settings 2026-07-11, Research/Content 2026-07-13) ALWAYS
 * resolve through their stack's explicit-screen navigator with a concrete
 * screen: a tab-level navigate only FOCUSES an already-populated stack — it
 * never resets it, so a bare-tab item is a no-op from any nested screen of
 * its own stack. The root fallbacks mean a future stacked-tab item that
 * forgets its screen still lands somewhere deterministic instead of silently
 * reintroducing the bug class.
 */
export function performNav(
  item: WebNavItem,
  nav: {
    navigateTab: (tab: WebNavTab) => void;
    navigateSettingsScreen: (screen: string) => void;
    navigateResearchScreen: (screen: string) => void;
    navigateContentScreen: (screen: string) => void;
  },
): void {
  if (item.pending) return;
  if (item.tab === 'Settings') {
    nav.navigateSettingsScreen(item.screen ?? SETTINGS_ROOT_SCREEN);
  } else if (item.tab === 'Research') {
    nav.navigateResearchScreen(item.screen ?? RESEARCH_ROOT_SCREEN);
  } else if (item.tab === 'Content') {
    nav.navigateContentScreen(item.screen ?? CONTENT_ROOT_SCREEN);
  } else if (item.tab) {
    // Home / Activity: stackless tabs — a bare focus is the whole job.
    nav.navigateTab(item.tab);
  }
}
