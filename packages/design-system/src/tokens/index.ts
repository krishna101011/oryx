export { colors, type Colors, oryxPalette, type OryxPalette } from './colors';
export {
  typography,
  type Typography,
  type TextVariant,
} from './typography';
export { spacing, type Spacing, type SpacingKey } from './spacing';
export { radius, type Radius, type RadiusKey } from './radius';

import { colors } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radius } from './radius';

/** Bundled theme object passed via ThemeProvider. */
export const theme = {
  mode: 'dark' as const,
  colors,
  typography,
  spacing,
  radius,
} as const;

export type Theme = typeof theme;
