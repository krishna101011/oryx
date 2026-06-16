import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '@oryx/design-system';
import type { IntelligenceStatus } from '@oryx/shared-types';
import { verificationStatusColor } from './statusColors';

const LABEL: Record<IntelligenceStatus, string> = {
  unverified: 'Unverified',
  verified: 'Verified',
  contested: 'Contested',
  analyst_approved: 'Approved',
  analyst_rejected: 'Rejected',
};

export const VerificationStatusPill: React.FC<{ status: IntelligenceStatus }> = ({
  status,
}) => (
  <View style={[styles.pill, { backgroundColor: verificationStatusColor(status) }]}>
    <Text variant="caption" color="inverse">
      {LABEL[status]}
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
