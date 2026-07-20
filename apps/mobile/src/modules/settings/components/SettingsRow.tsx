import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Icon, Pressable, Spacer, Text, useTheme, type IconName } from '@oryx/design-system';

/**
 * Accent family used to colour a row's icon by the section it belongs to.
 * Drawn from the "Midnight Citrus" decorative accent set; each maps directly
 * to a design-system accent token via the Icon component's color prop.
 */
export type SettingsRowAccent = 'amber' | 'coral' | 'teal' | 'slateBlue' | 'plum';

export interface SettingsRowProps {
  label: string;
  description?: string;
  icon: IconName;
  onPress?: () => void;
  trailing?: React.ReactNode;
  /** Section accent for the icon glyph. Defaults to amber (the brand accent). */
  accent?: SettingsRowAccent;
}

/**
 * Settings row anatomy (design-foundation wave, 2026-07-20) — rendered INSIDE
 * a section's HairlineRowList, not as its own standalone Card anymore (that
 * was the pre-migration one-card-per-row style, same class of change as
 * WorkspaceCard/RW-1). The enclosing Card + CardHeader supplies the section
 * frame; this row only owns icon + label + description + trailing chevron.
 */
export const SettingsRow: React.FC<SettingsRowProps> = ({
  label,
  description,
  icon,
  onPress,
  trailing,
  accent = 'amber',
}) => {
  const t = useTheme();
  const content = (
    <View style={styles.row}>
      <View
        style={[
          styles.iconWrap,
          { backgroundColor: t.colors.bg.elevated, borderRadius: t.radius.xl },
        ]}
      >
        <Icon name={icon} color={accent} />
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
  );
  return onPress ? <Pressable onPress={onPress}>{content}</Pressable> : content;
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  iconWrap: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
});
