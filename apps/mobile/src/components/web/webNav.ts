import type { GensparkIconName } from '@oryx/design-system';

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
      { id: 'verify', label: 'Verification Center', icon: 'Shield', tab: 'Settings', countKey: 'verifyPending' },
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
      { id: 'analytics', label: 'Analytics', icon: 'Bar', pending: true },
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
