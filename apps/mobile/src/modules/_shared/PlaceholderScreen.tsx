import React from 'react';
import { View, StyleSheet } from 'react-native';
import {
  Card,
  Icon,
  Screen,
  Spacer,
  Text,
  type IconName,
  useTheme,
} from '@oryx/design-system';

export interface PlaceholderScreenProps {
  title: string;
  description: string;
  icon: IconName;
  phase: string;
}

/**
 * Placeholder screen used by every module in Phase 1.
 *
 * Renders the module identity, what it will do, and which phase activates it.
 * This gives a navigable, premium-looking shell from day 1 without faking content.
 */
export const PlaceholderScreen: React.FC<PlaceholderScreenProps> = ({
  title,
  description,
  icon,
  phase,
}) => {
  const t = useTheme();
  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="display">{title}</Text>
      <Spacer size={2} />
      <Text variant="bodySm" color="secondary">
        {phase}
      </Text>
      <Spacer size={6} />
      <Card variant="default">
        <View style={styles.row}>
          <View
            style={[
              styles.iconWrap,
              { backgroundColor: t.colors.accent.tealGlow },
            ]}
          >
            <Icon name={icon} size="lg" color="brand" />
          </View>
          <View style={styles.body}>
            <Text variant="h2">Coming Soon</Text>
            <Spacer size={2} />
            <Text variant="body" color="secondary">
              {description}
            </Text>
          </View>
        </View>
      </Card>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  body: { flex: 1 },
});
