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
      { id: 'research', label: 'Research Workspace', icon: 'Beaker', tab: 'Research' },
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
      { id: 'content', label: 'Content Studio', icon: 'Pen', tab: 'Content', countKey: 'contentDrafts' },
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
      { id: 'settings', label: 'Settings', icon: 'Cog', tab: 'Settings' },
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

/**
 * Resolve a nav item to real navigation. Extracted from WebShell so the topbar
 * shortcuts (bell → 'activity', gear → 'settings') go through the exact same
 * resolution as a sidebar click, and so tests can inject recording fakes.
 * Pending items resolve to nothing — they have no built destination.
 */
export function performNav(
  item: WebNavItem,
  nav: {
    navigateTab: (tab: WebNavTab) => void;
    navigateSettingsScreen: (screen: string) => void;
  },
): void {
  if (item.pending) return;
  if (item.tab === 'Settings' && item.screen) {
    nav.navigateSettingsScreen(item.screen);
  } else if (item.tab) {
    nav.navigateTab(item.tab);
  }
}
