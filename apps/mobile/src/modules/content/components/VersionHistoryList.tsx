import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Spacer, Text, useTheme } from '@oryx/design-system';
import type { DraftVersion } from '@oryx/shared-types';

export const VersionHistoryList: React.FC<{ versions: DraftVersion[] }> = ({
  versions,
}) => {
  const t = useTheme();
  if (versions.length === 0) {
    return (
      <Text variant="caption" color="tertiary">
        No version history yet.
      </Text>
    );
  }
  return (
    <View>
      {versions.map((v) => (
        <View
          key={v.id}
          style={[styles.row, { borderBottomColor: t.colors.border.subtle }]}
        >
          <Text variant="bodySm">v{v.versionNumber}</Text>
          <Text variant="caption" color="tertiary">
            {v.isAiGenerated ? 'AI generated' : 'Analyst edit'}
            {v.wordCount != null ? ` · ${v.wordCount} words` : ''}
          </Text>
          <Spacer size={1} />
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  row: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    paddingVertical: 8,
  },
});
