import React from 'react';
import { View } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/**
 * Canonical ORYX horn mark — GENSPARK PORT (2026-06-29).
 *
 * Ported 1:1 from docs/design-reference/primitives.jsx <HornMark/>: the same
 * 200×200 viewBox, the same four bezier paths (two gradient-filled horns + two
 * inner-curl strokes). Gradient stops and the inner-curl stroke are read from
 * tokens (accent.brand / accent.brandSecondary / bg.primary). 2026-07-05 teal
 * retirement: those tokens now hold #08314A → #03121D (was #14B8A6 → #0E8C82).
 *
 * `glow` reproduces the source drop-shadow (RN has no SVG `filter`, so it is
 * approximated with a colored container shadow).
 */
export const HornMark: React.FC<{ size?: number; glow?: boolean }> = ({
  size = 56,
  glow = false,
}) => {
  const t = useTheme();
  const from = t.colors.accent.brand; // #08314A
  const to = t.colors.accent.brandSecondary; // #03121D
  const curl = t.colors.bg.primary; // #05070A

  const svg = (
    <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
      <Defs>
        <LinearGradient id="hornGrad" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={from} />
          <Stop offset="1" stopColor={to} />
        </LinearGradient>
      </Defs>
      {/* Left horn */}
      <Path
        d="M82 50 C 58 80, 56 130, 78 160 C 84 168, 90 168, 92 160 C 94 130, 96 100, 92 75 C 90 60, 86 52, 82 50 Z"
        fill="url(#hornGrad)"
      />
      {/* Right horn */}
      <Path
        d="M118 50 C 142 80, 144 130, 122 160 C 116 168, 110 168, 108 160 C 106 130, 104 100, 108 75 C 110 60, 114 52, 118 50 Z"
        fill="url(#hornGrad)"
      />
      {/* Inner curl detail */}
      <Path
        d="M88 60 C 78 88, 80 130, 90 152"
        stroke={curl}
        strokeWidth={3}
        fill="none"
        strokeLinecap="round"
      />
      <Path
        d="M112 60 C 122 88, 120 130, 110 152"
        stroke={curl}
        strokeWidth={3}
        fill="none"
        strokeLinecap="round"
      />
    </Svg>
  );

  if (!glow) return svg;
  return (
    <View
      style={{
        // source drop-shadow(0 0 18px <brand @ 0.5>) approximation
        shadowColor: from,
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 9,
        elevation: 0,
      }}
    >
      {svg}
    </View>
  );
};
