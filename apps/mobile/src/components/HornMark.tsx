import React from 'react';
import Svg, { Path } from 'react-native-svg';
import { useTheme } from '@oryx/design-system';

/**
 * Sparing oryx-horn motif — two open, teal-stroke curves rising from a shared
 * base, echoing the brand mark's line-art horns. No fill, rounded caps.
 *
 * Used ONLY by EmptyState (never headers, splash, or loading states) so the
 * motif stays a single, deliberate accent point. Stroke is the brand-secondary
 * token (#1E8F8F); never hardcode the hex (the no-raw-hex lint rule).
 */
export const HornMark: React.FC<{ size?: number }> = ({ size = 56 }) => {
  const t = useTheme();
  const stroke = t.colors.accent.brandSecondary;
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      style={{ opacity: 0.5 }}
    >
      <Path
        d="M28 47 C 21 40 15 31 18 17 C 19 13 22 11 24 10"
        stroke={stroke}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Path
        d="M28 47 C 35 40 41 31 38 17 C 37 13 34 11 32 10"
        stroke={stroke}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
};
