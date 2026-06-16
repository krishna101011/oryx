import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, useTheme } from '@oryx/design-system';
import type { SourceHealth } from '@oryx/shared-types';

/**
 * Small status chip (§15.5). Composes existing tokens only — no new ones.
 * Color is never the only signal (§8.8 rule 6): the label always renders.
 */
export const SourceHealthPill: React.FC<{ health: SourceHealth }> = ({ health }) => {
  const t = useTheme();
  const palette: Record<SourceHealth, { dot: string; label: string }> = {
    healthy: { dot: t.colors.semantic.success, label: 'Healthy' },
    degraded: { dot: t.colors.semantic.warning, label: 'Degraded' },
    auth_required: { dot: t.colors.semantic.danger, label: 'Auth lapsed' },
    disabled: { dot: t.colors.text.tertiary, label: 'Disabled' },
  };
  const { dot, label } = palette[health];
  return (
    <View
      style={[
        styles.pill,
        { borderColor: t.colors.border.default, backgroundColor: t.colors.bg.elevated },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: dot }]} />
      <Text variant="caption" color="secondary">
        {label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
});
