import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Card, Spacer, Text } from '@oryx/design-system';
import type { ContentDraft } from '@oryx/shared-types';
import { FormatBadge } from './FormatBadge';
import { DraftStatusPill } from './DraftStatusPill';

export const DraftCard: React.FC<{
  draft: ContentDraft;
  onPress: () => void;
}> = ({ draft, onPress }) => (
  <Pressable onPress={onPress}>
    <Card variant="elevated">
      <View style={styles.row}>
        <FormatBadge format={draft.format} />
        <DraftStatusPill status={draft.status} />
      </View>
      <Spacer size={2} />
      <Text variant="body">{draft.title}</Text>
      <Spacer size={1} />
      <Text variant="caption" color="tertiary">
        {draft.wordCount != null ? `${draft.wordCount} words · ` : ''}
        v{draft.currentVersion}
      </Text>
    </Card>
  </Pressable>
);

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
});
