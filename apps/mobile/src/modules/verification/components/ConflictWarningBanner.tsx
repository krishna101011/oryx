import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Icon, Text, useTheme, withAlpha } from '@oryx/design-system';

/**
 * Persistent banner shown on contested intelligence objects. It is never
 * dismissable — a contested object must always carry the warning.
 * The wash tracks semantic.danger, the same token its icon and copy read.
 */
export const ConflictWarningBanner: React.FC = () => {
  const t = useTheme();
  return (
    <View
      style={[
        styles.banner,
        { backgroundColor: withAlpha(t.colors.semantic.danger, 0.12) },
      ]}
    >
      <Icon name="TriangleAlert" color="danger" />
      <Text variant="bodySm" color="danger" style={styles.text}>
        This object has an unresolved conflict. Treat its claims with caution.
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    alignItems: 'center',
    borderRadius: 10,
    flexDirection: 'row',
    gap: 8,
    padding: 12,
  },
  text: {
    flex: 1,
  },
});
