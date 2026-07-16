export {
  colors,
  type Colors,
  lightColors,
  lightPalette,
  type LightPalette,
  lightGradients,
  oryxPalette,
  type OryxPalette,
  gensparkPalette,
  type GensparkPalette,
  gradients,
  type Gradients,
  withAlpha,
  channelColors,
  type ChannelColors,
} from './colors';
export {
  typography,
  fontFamilies,
  type Typography,
  type TextVariant,
} from './typography';
export { spacing, type Spacing, type SpacingKey } from './spacing';
export {
  radius,
  type Radius,
  type RadiusKey,
  gensparkRadius,
  type GensparkRadius,
} from './radius';
export { shadows, type Shadows } from './shadows';

import { colors, gradients, lightColors, lightGradients } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radius, gensparkRadius } from './radius';
import { shadows } from './shadows';

export type ThemeMode = 'dark' | 'light';

/**
 * Color/gradient leaves widened to `string` so one Theme type serves both
 * modes; typography/spacing/radius/shadows keep their exact (shared) types —
 * they are mode-invariant singletons referenced by both theme objects.
 */
type WidenLeaves<T> = {
  [K in keyof T]: T[K] extends string
    ? string
    : T[K] extends number
      ? number
      : WidenLeaves<T[K]>;
};

export interface Theme {
  mode: ThemeMode;
  colors: WidenLeaves<typeof colors>;
  gradients: WidenLeaves<typeof gradients>;
  typography: typeof typography;
  spacing: typeof spacing;
  radius: typeof radius;
  gensparkRadius: typeof gensparkRadius;
  shadows: typeof shadows;
}

const shared = { typography, spacing, radius, gensparkRadius, shadows };

export const darkTheme: Theme = { mode: 'dark', colors, gradients, ...shared };
export const lightTheme: Theme = {
  mode: 'light',
  colors: lightColors,
  gradients: lightGradients,
  ...shared,
};

/** Mode → theme registry consumed by the app's ThemeProvider wiring. */
export const themes: Record<ThemeMode, Theme> = {
  dark: darkTheme,
  light: lightTheme,
};

/** Bundled theme object passed via ThemeProvider. Dark is the default. */
export const theme = darkTheme;
