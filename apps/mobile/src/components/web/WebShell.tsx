import React, { useEffect, useState } from 'react';
import { Platform, Pressable, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useTheme } from '@oryx/design-system';
import { useMe } from '../../hooks/useMe';
import { useAppSelector } from '../../store';
import {
  navigateContentScreen,
  navigateResearchScreen,
  navigateSettingsScreen,
  navigateTab,
  navigationRef,
} from '../../navigation/navigationRef';
import type {
  ContentStackParamList,
  ResearchStackParamList,
  SettingsStackParamList,
} from '../../navigation/types';
import { WEB_NAV, type WebNavItem, performNav } from './webNav';
import { WebSearchOverlay } from './WebSearchOverlay';
import { WebSidebar } from './WebSidebar';
import { WebTopBar } from './WebTopBar';
import { SIDEBAR_WIDTH, activeNavIdFor, drawerNavigate, sidebarMode } from './webShellLayout';

function crumbsFor(activeId: string): [string, string] {
  for (const g of WEB_NAV) {
    const it = g.items.find((i) => i.id === activeId);
    if (it) return [g.group.charAt(0) + g.group.slice(1).toLowerCase(), it.label];
  }
  return ['Workspace', 'Command Center'];
}

/**
 * Web-only app shell. On `Platform.OS === 'web'` it frames the real navigator
 * inside the ported Genspark desktop layout (232px sidebar + 44px topbar +
 * scrolling main). On iOS/Android it is a pass-through — native keeps its
 * bottom-tab navigation untouched (early return introduces no extra View).
 *
 * Follows the WebFrame branching convention. The sidebar drives the real tab
 * navigator via navigationRef; only the four built tabs navigate, pending nav
 * items are inert.
 */
export const WebShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (Platform.OS !== 'web') return <>{children}</>;
  return <WebShellInner>{children}</WebShellInner>;
};

const WebShellInner: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const t = useTheme();
  const status = useAppSelector((s) => s.auth.status);
  const me = useMe();
  const [activeId, setActiveId] = useState('home');
  const [searchOpen, setSearchOpen] = useState(false);
  // Below the derived breakpoint (see webShellLayout.ts) the fixed 232px
  // sidebar would crowd content, so it collapses into a topbar hamburger
  // opening an overlay drawer. useWindowDimensions re-renders on resize.
  const { width } = useWindowDimensions();
  const collapsed = sidebarMode(width) === 'collapsed';
  const [navOpen, setNavOpen] = useState(false);

  // The topbar's ⌘K badge is a real shortcut: Cmd+K (mac) / Ctrl+K opens the
  // search overlay from anywhere in the app chrome.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // Navigation state is the single source of truth for the active nav id.
  // (No optimistic set on click — a second writer raced this listener and
  // left a stale highlight whenever the click was a same-tab no-op.)
  useEffect(() => {
    const sync = () => {
      if (!navigationRef.isReady()) return;
      const route = navigationRef.getCurrentRoute();
      // current route name may be a nested screen; match the top tab by walking state
      const state = navigationRef.getRootState();
      const tabsRoute = state.routes.find((r) => r.name === 'Tabs');
      const tabState = tabsRoute?.state as { routes?: { name: string }[]; index?: number } | undefined;
      const tabName =
        tabState?.routes && typeof tabState.index === 'number'
          ? tabState.routes[tabState.index]?.name
          : route?.name;
      // getCurrentRoute() is the deepest focused screen — activeNavIdFor uses
      // it to disambiguate the Settings-tab nav items (verify/automation/
      // analytics); null keeps the previous highlight (no-op navigations).
      const id = activeNavIdFor(tabName, route?.name);
      if (id) setActiveId(id);
    };
    const unsub = navigationRef.addListener?.('state', sync);
    sync();
    return () => unsub?.();
  }, []);

  const onNavigate = (item: WebNavItem) => {
    performNav(item, {
      navigateTab,
      navigateSettingsScreen: (screen) =>
        navigateSettingsScreen(screen as keyof SettingsStackParamList),
      navigateResearchScreen: (screen) =>
        navigateResearchScreen(screen as keyof ResearchStackParamList),
      navigateContentScreen: (screen) =>
        navigateContentScreen(screen as keyof ContentStackParamList),
    });
  };

  // Drawer presses resolve through the SAME performNav via drawerNavigate —
  // nav resolution must never fork by viewport (third bug in this area).
  const onDrawerNavigate = (item: WebNavItem) =>
    drawerNavigate(item, { close: () => setNavOpen(false), perform: onNavigate });

  // Only show the desktop chrome once the user is fully into the app. Auth and
  // onboarding render full-bleed (no sidebar), matching their mobile UX.
  const showChrome =
    status === 'authenticated' && me.data?.onboarding?.state === 'complete';

  if (!showChrome) {
    return <View style={{ flex: 1, backgroundColor: t.colors.bg.primary }}>{children}</View>;
  }

  return (
    <View style={{ flex: 1, flexDirection: 'row', backgroundColor: t.colors.bg.primary }}>
      {!collapsed ? <WebSidebar me={me.data} activeId={activeId} onNavigate={onNavigate} /> : null}
      <View style={{ flex: 1, minWidth: 0 }}>
        <WebTopBar
          crumbs={crumbsFor(activeId)}
          me={me.data}
          onNavigate={onNavigate}
          onOpenSearch={() => setSearchOpen(true)}
          onOpenNav={collapsed ? () => setNavOpen(true) : undefined}
        />
        <View style={{ flex: 1, minHeight: 0 }}>{children}</View>
      </View>
      {collapsed && navOpen ? (
        // Overlay drawer, NOT push-content: the WebSearchOverlay backdrop
        // convention (absolute rgba(0,0,0,0.55) Pressable-to-close), with the
        // SAME WebSidebar and the SAME activeId the expanded rail shows.
        <Pressable
          style={styles.drawerBackdrop}
          onPress={() => setNavOpen(false)}
          accessibilityLabel="Close navigation"
        >
          <Pressable style={styles.drawerPanel} onPress={(e) => e.stopPropagation()}>
            <WebSidebar me={me.data} activeId={activeId} onNavigate={onDrawerNavigate} />
          </Pressable>
        </Pressable>
      ) : null}
      {searchOpen ? (
        <WebSearchOverlay
          onClose={() => setSearchOpen(false)}
          // Both destinations name an explicit nested Settings screen — the
          // convention the two 2026-07-11 nav bugs established (a bare tab
          // navigate never resets a populated stack).
          onOpenSource={(sourceId) => {
            setSearchOpen(false);
            navigateSettingsScreen('IntakeSourceDetail', { sourceId });
          }}
          onOpenItem={(itemId) => {
            setSearchOpen(false);
            navigateSettingsScreen('IntakeItemDetail', { itemId });
          }}
        />
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  // WebSearchOverlay backdrop convention; zIndex under search (1000) so ⌘K
  // opened from the drawer still layers above it.
  drawerBackdrop: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(0,0,0,0.55)',
    zIndex: 900,
  },
  drawerPanel: { width: SIDEBAR_WIDTH, height: '100%' },
});
