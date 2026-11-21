import React from 'react';
import { View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

export interface OryxMarkProps {
  size?: number;
  glow?: boolean;
}

/**
 * The approved ORYX identity mark (concept A), traced from the selected artwork.
 *
 * The two solid, mirrored silhouettes are native SVG paths, not a raster image.
 * The active theme's primary text colour keeps the mark legible on light and
 * dark surfaces while preserving the original single-colour identity.
 */
export const OryxMark: React.FC<OryxMarkProps> = ({ size = 56, glow = false }) => {
  const theme = useTheme();
  const markColor = theme.colors.text.primary;

  const mark = (
    <Svg width={size} height={size} viewBox="0 0 304 304" fill="none">
      <Path
        d="M18 35 C15.48 38.92 11.83 42.5 9 49 C6.17 55.5 2.33 65.33 1 74 C-0.33 82.67 -0.17 92.5 1 101 C2.17 109.5 5.5 118.67 8 125 C10.5 131.33 11.17 133.17 16 139 C20.83 144.83 24.83 151.5 37 160 C49.17 168.5 76.67 181.67 89 190 C101.33 198.33 104.17 202.17 111 210 C117.83 217.83 124.67 227.5 130 237 C135.33 246.5 139.36 258.6 143 267 C142.44 249.92 142 219.17 141 206 C140 192.83 138.83 193.67 137 188 C135.17 182.33 132.67 176.67 130 172 C127.33 167.33 124.83 164 121 160 C117.17 156 118.83 154.67 107 148 C95.17 141.33 62.17 126.67 50 120 C37.83 113.33 38 111.5 34 108 C30 104.5 28.67 102.83 26 99 C23.33 95.17 20 89.67 18 85 C16 80.33 14.67 76.83 14 71 C13.33 65.17 13.33 56 14 50 C14.67 44 16.88 39.2 18 35 Z"
        fill={markColor}
      />
      <Path
        d="M285 34 C286.12 37.92 288.17 42.83 289 48 C289.83 53.17 290.5 59 290 65 C289.5 71 288 78.33 286 84 C284 89.67 281.17 94.5 278 99 C274.83 103.5 271.5 107.17 267 111 C262.5 114.83 258.67 118 251 122 C243.33 126 230.17 130.5 221 135 C211.83 139.5 203.67 143 196 149 C188.33 155 180.33 162 175 171 C169.67 180 166.33 192.33 164 203 C161.67 213.67 161.5 224 161 235 C160.5 246 161 259.48 161 269 C165.2 259.2 170 244.5 176 234 C182 223.5 189.17 214.17 197 206 C204.83 197.83 210.83 193 223 185 C235.17 177 258.5 166.67 270 158 C281.5 149.33 286.83 140.83 292 133 C297.17 125.17 299.17 120 301 111 C302.83 102 303.67 88.33 303 79 C302.33 69.67 300 62.5 297 55 C294 47.5 288.36 39.88 285 34 Z"
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
