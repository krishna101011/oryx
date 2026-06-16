import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Pressable, Spacer, Text, useTheme } from '@oryx/design-system';

export interface ChoiceTileProps {
  label: string;
  description?: string;
  selected: boolean;
  onPress: () => void;
}

export const ChoiceTile: React.FC<ChoiceTileProps> = ({
  label,
  description,
  selected,
  onPress,
}) => {
  const t = useTheme();
  return (
    <Pressable onPress={onPress}>
      <Card variant="default" style={selected ? styles.selectedCard(t) : undefined}>
        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text variant="h2">{label}</Text>
            {description ? (
              <>
                <Spacer size={1} />
                <Text variant="bodySm" color="secondary">
                  {description}
                </Text>
              </>
            ) : null}
          </View>
          <View
            style={[
              styles.dot,
              {
                borderColor: selected
                  ? t.colors.accent.teal
                  : t.colors.border.strong,
                backgroundColor: selected
                  ? t.colors.accent.teal
                  : 'transparent',
              },
            ]}
          />
        </View>
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create<any>({
  row: { flexDirection: 'row', alignItems: 'center' },
  dot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    marginLeft: 12,
  },
  selectedCard: (t: any) => ({
    borderColor: t.colors.accent.teal,
    borderWidth: 1,
  }),
});
