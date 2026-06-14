import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Pressable, Spacer, Text } from '@anant/design-system';
import type { ResearchWorkspace } from '@anant/shared-types';

export const WorkspaceCard: React.FC<{
  workspace: ResearchWorkspace;
  itemCount?: number;
  onPress?: () => void;
}> = ({ workspace, itemCount, onPress }) => (
  <Pressable onPress={onPress}>
    <Card variant="elevated">
      <View style={styles.head}>
        <Text variant="bodySm">{workspace.name}</Text>
        <Text variant="caption" color="tertiary">
          {workspace.status}
        </Text>
      </View>
      {workspace.description ? (
        <>
          <Spacer size={1} />
          <Text variant="caption" color="secondary">
            {workspace.description}
          </Text>
        </>
      ) : null}
      {itemCount !== undefined ? (
        <>
          <Spacer size={2} />
          <Text variant="caption" color="tertiary">
            {itemCount} object{itemCount === 1 ? '' : 's'}
          </Text>
        </>
      ) : null}
    </Card>
  </Pressable>
);

const styles = StyleSheet.create({
  head: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
