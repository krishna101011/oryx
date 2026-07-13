import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Defs, Ellipse, RadialGradient, Stop } from 'react-native-svg';
import { useTheme } from '@oryx/design-system';

/**
 * The Command Center hero's atmospheric radial wash — a 1:1 port of the
 * reference's two-stop background (command-center.jsx:38):
 *   radial-gradient(ellipse at 70% 30%, rgba(139,92,246,0.10), transparent 60%),
 *   radial-gradient(ellipse at 20% 80%, rgba(20,184,166,0.06), transparent 50%)
 * built from EXISTING tokens only: the violet stop is accent.plum, and the
 * source's rgba(20,184,166,…) is the retired teal #14B8A6 — per the
 * 2026-07-05 teal retirement every wash tracks the current --teal token
 * (accent.teal), so the second ellipse takes that value at the same 0.06.
 * CSS radial-gradient has no RN equivalent, so this is react-native-svg
 * (the Spark/Candles/HornMark precedent), absolutely filled behind the hero.
 */
export const HeroWash: React.FC = () => {
  const t = useTheme();
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
        <Defs>
          <RadialGradient id="heroWashViolet">
            <Stop offset="0" stopColor={t.colors.accent.plum} stopOpacity={0.1} />
            <Stop offset="0.6" stopColor={t.colors.accent.plum} stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="heroWashTeal">
            <Stop offset="0" stopColor={t.colors.accent.teal} stopOpacity={0.06} />
            <Stop offset="0.5" stopColor={t.colors.accent.teal} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Ellipse cx="70" cy="30" rx="70" ry="60" fill="url(#heroWashViolet)" />
        <Ellipse cx="20" cy="80" rx="60" ry="50" fill="url(#heroWashTeal)" />
      </Svg>
    </View>
  );
};
