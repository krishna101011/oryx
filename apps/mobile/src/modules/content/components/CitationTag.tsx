import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, useTheme } from '@oryx/design-system';

/**
 * Provenance chip — references an intelligence object a draft drew from.
 * Wave A surfaces the object id (shortened); later waves resolve headlines.
 */
export const CitationTag: React.FC<{ label: string }> = ({ label }) => {
  const t = useTheme();
  return (
    <View style={[styles.tag, { borderColor: t.colors.border.subtle }]}>
      <Text variant="caption" color="secondary">
        {label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  tag: {
    alignSelf: 'flex-start',
    borderRadius: 6,
    borderWidth: 1,
    marginBottom: 6,
    marginRight: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
});
