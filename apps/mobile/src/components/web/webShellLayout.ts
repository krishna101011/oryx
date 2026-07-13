import type { WebNavItem } from './webNav';

/**
 * Web shell responsive layout — pure, node:test-testable (the screen-logic
 * extraction convention).
 *
 * Live-observed problem (2026-07-13): the sidebar is a FIXED 232px column
 * (design-system genspark.ts:105, a 1:1 port of the reference .sidebar) with
 * no collapse logic anywhere, so at narrow window widths it eats the content
 * area — a 390px window leaves ~268px of content. The Genspark reference has
 * no responsive pattern to port, and native has no drawer to reuse (it
 * navigates by bottom tabs), so the breakpoint below is DERIVED from a real
 * screen's minimum usable content width rather than copied or guessed.
 */

/** The sidebar's real fixed width — gx.sidebar (genspark.ts:105). */
export const SIDEBAR_WIDTH = 232;

/**
 * Minimum usable content width, reasoned from Command Center (the wave that
 * established the narrow-width layout): its KPI tiles are usable down to the
 * 2-up wrap point — two tiles at their 150px floor plus the 12px flex gap
 * (DashboardScreen.tsx styles.kpiTile/kpiRow) — inside Screen's canonical
 * spacing[4]=16 horizontal padding per side. Below this the densest built
 * screen degrades to a cramped 1-up column.
 */
export const MIN_CONTENT_WIDTH = 150 * 2 + 12 + 16 * 2; // = 344

/**
 * Window width below which the fixed sidebar genuinely crowds content:
 * its own 232px plus the 344px content floor = 576. At ≥576 the expanded
 * sidebar leaves every built screen usable; below, it collapses to a topbar
 * hamburger opening an OVERLAY drawer (content keeps the full window width).
 */
export const SIDEBAR_COLLAPSE_BREAKPOINT = SIDEBAR_WIDTH + MIN_CONTENT_WIDTH;

export type SidebarMode = 'expanded' | 'collapsed';

export function sidebarMode(windowWidth: number): SidebarMode {
  return windowWidth < SIDEBAR_COLLAPSE_BREAKPOINT ? 'collapsed' : 'expanded';
}

/**
 * A drawer press must close the drawer AND resolve through the exact same
 * performNav the expanded sidebar uses — nav resolution must not fork by
 * viewport (this area has produced three real bugs; a second resolution path
 * is how the next one happens). Close-before-navigate so the drawer never
 * lingers over the destination screen.
 */
export function drawerNavigate(
  item: WebNavItem,
  deps: { close: () => void; perform: (item: WebNavItem) => void },
): void {
  deps.close();
  deps.perform(item);
}

// ---------------------------------------------------------------------------
// Active-item highlight (extracted from WebShell so the mapping that drives
// BOTH the expanded sidebar and the collapsed drawer is testable).
// ---------------------------------------------------------------------------

/** tab route name → web nav id, to mirror back-button / deep-link navigation. */
const TAB_TO_NAV: Record<string, string> = {
  Home: 'home',
  Research: 'research',
  Content: 'content',
  Activity: 'activity',
  Settings: 'settings',
};

/**
 * Verification surfaces are nested inside the Settings tab's stack, and the
 * sidebar has two items pointing at that tab ('settings' and 'verify'). The
 * tab name alone is ambiguous for them — the focused nested screen decides.
 */
const VERIFY_SCREENS = new Set([
  'VerificationQueue',
  'ConflictReview',
  'ClaimDetail',
  'SourceCredibility',
  'IntelligenceObjectDetail',
]);

/** Same disambiguation for the Automation Hub, also nested under Settings. */
const AUTOMATION_SCREENS = new Set(['AutomationHub']);

/** And for the Analytics dashboard (Phase 7 Wave B), nested under Settings. */
const ANALYTICS_SCREENS = new Set(['Analytics']);

/**
 * The nav id to highlight for a focused (tab, deepest screen) pair, or null
 * when the pair names no navigable tab (caller keeps the previous highlight —
 * the no-op-navigate rule from the 2026-07-12 stale-highlight fix).
 */
export function activeNavIdFor(
  tabName: string | undefined,
  focusedScreen: string | undefined,
): string | null {
  if (!tabName || !TAB_TO_NAV[tabName]) return null;
  if (tabName === 'Settings' && focusedScreen) {
    if (VERIFY_SCREENS.has(focusedScreen)) return 'verify';
    if (AUTOMATION_SCREENS.has(focusedScreen)) return 'automation';
    if (ANALYTICS_SCREENS.has(focusedScreen)) return 'analytics';
  }
  return TAB_TO_NAV[tabName]!;
}
