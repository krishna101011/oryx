import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Icon, Text } from '@anant/design-system';

/**
 * Persistent banner shown on contested intelligence objects. It is never
 * dismissable — a contested object must always carry the warning.
 */
export const ConflictWarningBanner: React.FC = () => (
  <View style={styles.banner}>
    <Icon name="TriangleAlert" color="danger" />
    <Text variant="bodySm" color="danger" style={styles.text}>
      This object has an unresolved conflict. Treat its claims with caution.
    </Text>
  </View>
);

const styles = StyleSheet.create({
  banner: {
    alignItems: 'center',
    backgroundColor: 'rgba(239,68,68,0.12)',
    borderRadius: 10,
    flexDirection: 'row',
    gap: 8,
    padding: 12,
  },
  text: {
    flex: 1,
  },
});
