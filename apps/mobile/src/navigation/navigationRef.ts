import { createNavigationContainerRef } from '@react-navigation/native';
import type { RootStackParamList } from './types';

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
