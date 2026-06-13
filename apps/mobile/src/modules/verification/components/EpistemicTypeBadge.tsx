import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '@anant/design-system';
import type { EpistemicType } from '@anant/shared-types';

/** Compact label for a claim's epistemic type (ADR-036). */
export const EpistemicTypeBadge: React.FC<{ type: EpistemicType }> = ({ type }) => (
  <View style={styles.badge}>
    <Text variant="caption" color="secondary">
      {type}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(127,127,127,0.15)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
});
