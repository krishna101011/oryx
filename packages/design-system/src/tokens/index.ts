export {
  colors,
  type Colors,
  oryxPalette,
  type OryxPalette,
  gensparkPalette,
  type GensparkPalette,
  gradients,
  type Gradients,
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

import { colors, gradients } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radius, gensparkRadius } from './radius';
import { shadows } from './shadows';

/** Bundled theme object passed via ThemeProvider. */
export const theme = {
  mode: 'dark' as const,
  colors,
  gradients,
  typography,
  spacing,
  radius,
  gensparkRadius,
  shadows,
} as const;

export type Theme = typeof theme;
