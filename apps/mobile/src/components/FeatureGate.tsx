import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Icon, Spacer, Text, useTheme, type IconName } from '@anant/design-system';
import type { FlagKey } from '@anant/shared-types';
import { useMe } from '../hooks/useMe';

export interface FeatureGateProps {
  flag: FlagKey;
  children: React.ReactNode;
  /** Friendly name used in the "Coming Soon" fallback. */
  name?: string;
  icon?: IconName;
  fallback?: React.ReactNode;
}

/**
 * Gates a screen on a feature flag.
 * - On: renders children.
 * - Off: renders the fallback (or a default "Coming Soon" tile).
 */
export const FeatureGate: React.FC<FeatureGateProps> = ({
  flag,
  children,
  name,
  icon = 'Lock',
  fallback,
}) => {
  const me = useMe();
  const enabled = me.data?.flags?.[flag] ?? false;
  if (enabled) return <>{children}</>;
  if (fallback) return <>{fallback}</>;
  return <ComingSoonTile name={name ?? flag} icon={icon} />;
};

const ComingSoonTile: React.FC<{ name: string; icon: IconName }> = ({
  name,
  icon,
}) => {
  const t = useTheme();
  return (
    <View style={styles.wrap}>
      <Spacer size={6} />
      <Card variant="default">
        <View style={styles.row}>
          <View style={[styles.iconWrap, { backgroundColor: t.colors.accent.goldGlow }]}>
            <Icon name={icon} size="lg" color="gold" />
          </View>
          <View style={styles.body}>
            <Text variant="h2">{name}</Text>
            <Spacer size={2} />
            <Text variant="body" color="secondary">
              Coming soon.
            </Text>
          </View>
        </View>
      </Card>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { paddingHorizontal: 16 },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconWrap: {
    width: 44, height: 44, borderRadius: 12,
    alignItems: 'center', justifyContent: 'center', marginRight: 16,
  },
  body: { flex: 1 },
});
