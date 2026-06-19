import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '@oryx/design-system';
import type { DraftStatus } from '@oryx/shared-types';
import { DRAFT_STATUS_LABEL, draftStatusColor } from '../theme/draftColors';

export const DraftStatusPill: React.FC<{ status: DraftStatus }> = ({ status }) => (
  <View style={[styles.pill, { backgroundColor: draftStatusColor(status) }]}>
    <Text variant="caption" color="inverse">
      {DRAFT_STATUS_LABEL[status]}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
});
