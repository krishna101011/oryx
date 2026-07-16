import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, useTheme, withAlpha } from '@oryx/design-system';
import type { EpistemicType } from '@oryx/shared-types';

/** Compact label for a claim's epistemic type (ADR-036). */
export const EpistemicTypeBadge: React.FC<{ type: EpistemicType }> = ({ type }) => {
  const t = useTheme();
  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: withAlpha(t.colors.text.tertiary, 0.15) },
      ]}
    >
      <Text variant="caption" color="secondary">
        {type}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
});
