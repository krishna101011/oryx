import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, useTheme, withAlpha } from '@oryx/design-system';
import { SEVERITY_INDIGO } from './severityColors';

/**
 * Horizontal confidence bar, 0.0–1.0. A null score (unscorable / unclassified
 * claim) renders as "Unscored" with an empty track. The fill is the
 * spec-locked severity indigo (mode-invariant); the track is a theme-aware
 * neutral wash.
 */
export const ConfidenceMeter: React.FC<{ score: number | null }> = ({ score }) => {
  const t = useTheme();
  const pct = score === null ? 0 : Math.round(Math.min(1, Math.max(0, score)) * 100);
  return (
    <View style={styles.wrap}>
      <View
        style={[
          styles.track,
          { backgroundColor: withAlpha(t.colors.text.tertiary, 0.2) },
        ]}
      >
        <View style={[styles.fill, { width: `${pct}%` }]} />
      </View>
      <Text variant="caption" color="secondary">
        {score === null ? 'Unscored' : `${pct}%`}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    gap: 4,
  },
  track: {
    borderRadius: 999,
    height: 6,
    overflow: 'hidden',
    width: '100%',
  },
  fill: {
    backgroundColor: SEVERITY_INDIGO,
    borderRadius: 999,
    height: 6,
  },
});
