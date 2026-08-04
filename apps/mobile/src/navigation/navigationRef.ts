import { createNavigationContainerRef } from '@react-navigation/native';
import type {
  AcademyStackParamList,
  ContentStackParamList,
  ResearchStackParamList,
  RootStackParamList,
  SettingsStackParamList,
  TeamStackParamList,
} from './types';

/**
 * Container-level navigation ref. Lets the web-only sidebar (which renders
 * OUTSIDE the NavigationContainer subtree) drive the real tab navigator, and
 * lets it read the current tab to highlight the active nav item.
 */
export const navigationRef = createNavigationContainerRef<RootStackParamList>();

/** Navigate to a top-level tab from the web sidebar. No-op until ready. */
export function navigateTab(
  tab: 'Home' | 'Research' | 'Content' | 'Team' | 'Academy' | 'Activity' | 'Settings',
): void {
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

/**
 * Research/Content mirrors of navigateSettingsScreen (2026-07-13, third
 * instance of the bare-tab bug class): a tab-level navigate only FOCUSES a
 * populated stack, so their sidebar items need the same explicit-screen path
 * the Settings-tab family got on 2026-07-11.
 */
export function navigateResearchScreen<S extends keyof ResearchStackParamList>(
  screen: S,
  params?: ResearchStackParamList[S],
): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', {
    screen: 'Research',
    params: params === undefined ? { screen } : { screen, params },
  } as never);
}

export function navigateContentScreen<S extends keyof ContentStackParamList>(
  screen: S,
  params?: ContentStackParamList[S],
): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', {
    screen: 'Content',
    params: params === undefined ? { screen } : { screen, params },
  } as never);
}

/** Team promotion wave (2026-07-26) — same mirror, fourth stacked tab. */
export function navigateTeamScreen<S extends keyof TeamStackParamList>(
  screen: S,
  params?: TeamStackParamList[S],
): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', {
    screen: 'Team',
    params: params === undefined ? { screen } : { screen, params },
  } as never);
}

/** Phase 8 Wave C — same mirror, fifth stacked tab (Academy activation). */
export function navigateAcademyScreen<S extends keyof AcademyStackParamList>(
  screen: S,
  params?: AcademyStackParamList[S],
): void {
  if (!navigationRef.isReady()) return;
  navigationRef.navigate('Tabs', {
    screen: 'Academy',
    params: params === undefined ? { screen } : { screen, params },
  } as never);
}
