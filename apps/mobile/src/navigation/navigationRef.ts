import { createNavigationContainerRef } from '@react-navigation/native';
import type { RootStackParamList, SettingsStackParamList } from './types';

/**
 * Container-level navigation ref. Lets the web-only sidebar (which renders
 * OUTSIDE the NavigationContainer subtree) drive the real tab navigator, and
 * lets it read the current tab to highlight the active nav item.
 */
export const navigationRef = createNavigationContainerRef<RootStackParamList>();

/** Navigate to a top-level tab from the web sidebar. No-op until ready. */
export function navigateTab(tab: 'Home' | 'Research' | 'Content' | 'Activity' | 'Settings'): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', { screen: tab });
}

/**
 * Navigate to a screen nested in the Settings stack (sidebar deep items,
 * search results). `params` carries the screen's route params for
 * param-taking destinations (e.g. IntakeItemDetail { itemId }).
 */
export function navigateSettingsScreen<S extends keyof SettingsStackParamList>(
  screen: S,
  params?: SettingsStackParamList[S],
): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', {
    screen: 'Settings',
    params: params === undefined ? { screen } : { screen, params },
  } as never);
}
