import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Icon, Pressable, Spacer, Text, useTheme, type IconName } from '@anant/design-system';

export interface SettingsRowProps {
  label: string;
  description?: string;
  icon: IconName;
  onPress?: () => void;
  trailing?: React.ReactNode;
}

export const SettingsRow: React.FC<SettingsRowProps> = ({
  label,
  description,
  icon,
  onPress,
  trailing,
}) => {
  const t = useTheme();
  const content = (
    <Card variant="default">
      <View style={styles.row}>
        <View style={[styles.iconWrap, { backgroundColor: t.colors.accent.goldGlow }]}>
          <Icon name={icon} color="gold" />
        </View>
        <View style={{ flex: 1 }}>
          <Text variant="body">{label}</Text>
          {description ? (
            <>
              <Spacer size={1} />
              <Text variant="bodySm" color="secondary">
                {description}
              </Text>
            </>
          ) : null}
        </View>
        {trailing ?? <Icon name="ChevronRight" color="tertiary" />}
      </View>
    </Card>
  );
  return onPress ? <Pressable onPress={onPress}>{content}</Pressable> : content;
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  iconWrap: {
    width: 36, height: 36, borderRadius: 8,
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
});
