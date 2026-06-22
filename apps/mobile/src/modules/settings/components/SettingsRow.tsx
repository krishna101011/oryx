import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Icon, Pressable, Spacer, Text, useTheme, type IconName } from '@oryx/design-system';

/**
 * Accent family used to colour a row's icon by the section it belongs to.
 * These map to existing design-system accent tokens — 'teal' resolves via the
 * Icon component's 'brand' keyword; the rest are exposed directly by Icon.
 */
export type SettingsRowAccent = 'teal' | 'indigo' | 'violet' | 'blue';

export interface SettingsRowProps {
  label: string;
  description?: string;
  icon: IconName;
  onPress?: () => void;
  trailing?: React.ReactNode;
  /** Section accent for the icon glyph. Defaults to teal (the brand accent). */
  accent?: SettingsRowAccent;
}

export const SettingsRow: React.FC<SettingsRowProps> = ({
  label,
  description,
  icon,
  onPress,
  trailing,
  accent = 'teal',
}) => {
  const t = useTheme();
  const iconColor = accent === 'teal' ? 'brand' : accent;
  const content = (
    <Card variant="default">
      <View style={styles.row}>
        <View style={[styles.iconWrap, { backgroundColor: t.colors.bg.elevated }]}>
          <Icon name={icon} color={iconColor} />
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
