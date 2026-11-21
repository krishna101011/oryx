import React from 'react';
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

export interface OryxMarkProps {
  size?: number;
  glow?: boolean;
}

/**
 * The approved ORYX identity mark (concept A).
 *
 * Two mirrored, solid silhouettes form the twin-horn symbol. The mark uses
 * the active theme's primary text colour so it remains crisp on both light
 * and dark surfaces without introducing a second, competing brand accent.
 */
export const OryxMark: React.FC<OryxMarkProps> = ({ size = 56, glow = false }) => {
  const theme = useTheme();
  const markColor = theme.colors.text.primary;

  const mark = (
    <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
      <Path
        d="M50 12 C25 43 28 74 56 94 C80 111 92 128 94 153 C95 166 94 179 92 190 C86 164 72 149 49 136 C18 118 4 91 4 62 C4 42 21 23 50 12 Z"
        fill={markColor}
      />
      <Path
        d="M150 12 C175 43 172 74 144 94 C120 111 108 128 106 153 C105 166 106 179 108 190 C114 164 128 149 151 136 C182 118 196 91 196 62 C196 42 179 23 150 12 Z"
        fill={markColor}
      />
    </Svg>
  );

  if (!glow) return mark;

  return (
    <View
      style={{
        shadowColor: markColor,
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.22,
        shadowRadius: 8,
        elevation: 0,
      }}
    >
      {mark}
    </View>
  );
};
