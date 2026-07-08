import React, { useEffect, useState } from 'react';
import { Platform, View } from 'react-native';
import { useTheme } from '@oryx/design-system';
import { useMe } from '../../hooks/useMe';
import { useAppSelector } from '../../store';
import { navigateSettingsScreen, navigateTab, navigationRef } from '../../navigation/navigationRef';
import type { SettingsStackParamList } from '../../navigation/types';
import { WEB_NAV, type WebNavItem } from './webNav';
import { WebSidebar } from './WebSidebar';
import { WebTopBar } from './WebTopBar';

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
      if (!tabName || !TAB_TO_NAV[tabName]) return;
      // getCurrentRoute() is the deepest focused screen — it disambiguates the
      // two Settings-tab nav items (verification screens → 'verify').
      const focusedScreen = route?.name;
      let id = TAB_TO_NAV[tabName]!;
      if (tabName === 'Settings' && focusedScreen) {
        if (VERIFY_SCREENS.has(focusedScreen)) id = 'verify';
        else if (AUTOMATION_SCREENS.has(focusedScreen)) id = 'automation';
        else if (ANALYTICS_SCREENS.has(focusedScreen)) id = 'analytics';
      }
      setActiveId(id);
    };
    const unsub = navigationRef.addListener?.('state', sync);
    sync();
    return () => unsub?.();
  }, []);

  const onNavigate = (item: WebNavItem) => {
    if (item.tab === 'Settings' && item.screen) {
      navigateSettingsScreen(item.screen as keyof SettingsStackParamList);
    } else if (item.tab) {
      navigateTab(item.tab);
    }
  };

  // Only show the desktop chrome once the user is fully into the app. Auth and
  // onboarding render full-bleed (no sidebar), matching their mobile UX.
  const showChrome =
    status === 'authenticated' && me.data?.onboarding?.state === 'complete';

  if (!showChrome) {
    return <View style={{ flex: 1, backgroundColor: t.colors.bg.primary }}>{children}</View>;
  }

  return (
    <View style={{ flex: 1, flexDirection: 'row', backgroundColor: t.colors.bg.primary }}>
      <WebSidebar me={me.data} activeId={activeId} onNavigate={onNavigate} />
      <View style={{ flex: 1, minWidth: 0 }}>
        <WebTopBar crumbs={crumbsFor(activeId)} />
        <View style={{ flex: 1, minHeight: 0 }}>{children}</View>
      </View>
    </View>
  );
};
