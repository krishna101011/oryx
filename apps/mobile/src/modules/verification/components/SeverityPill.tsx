import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '@anant/design-system';
import { SEVERITY_AMBER, SEVERITY_INDIGO, SEVERITY_RED } from './severityColors';

/**
 * Conflict severity pill. Colors are fixed by the Wave D spec:
 *   severity > 0.7   → red    (#EF4444)
 *   0.3 ≤ s ≤ 0.7    → amber  (#F59E0B)
 *   severity < 0.3   → indigo (#6366F1)
 */
export function severityColor(severity: number): string {
  if (severity > 0.7) return SEVERITY_RED;
  if (severity >= 0.3) return SEVERITY_AMBER;
  return SEVERITY_INDIGO;
}

export const SeverityPill: React.FC<{ severity: number }> = ({ severity }) => (
  <View style={[styles.pill, { backgroundColor: severityColor(severity) }]}>
    <Text variant="caption" color="inverse">
      {severity.toFixed(2)}
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
