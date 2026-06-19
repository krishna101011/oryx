import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '@oryx/design-system';
import type { ContentFormat } from '@oryx/shared-types';
import { FORMAT_LABEL, formatColor } from '../theme/draftColors';

export const FormatBadge: React.FC<{ format: ContentFormat }> = ({ format }) => (
  <View style={[styles.badge, { backgroundColor: formatColor(format) }]}>
    <Text variant="caption" color="inverse">
      {FORMAT_LABEL[format]}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
});
