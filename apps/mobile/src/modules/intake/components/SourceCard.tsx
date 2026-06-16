import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Icon, Pressable, Spacer, Text, type IconName } from '@oryx/design-system';
import type { IntakeSource } from '@oryx/shared-types';
import { SourceHealthPill } from './SourceHealthPill';

const KIND_ICONS: Record<IntakeSource['kind'], IconName> = {
  gmail: 'Mail',
  rss: 'Rss',
  webhook: 'Webhook',
  api_pull: 'Plug',
  manual: 'PenLine',
};

const KIND_LABELS: Record<IntakeSource['kind'], string> = {
  gmail: 'Gmail',
  rss: 'RSS feed',
  webhook: 'Webhook',
  api_pull: 'API pull',
  manual: 'Manual',
};

function lastSyncLabel(lastSyncedAt: string | null): string {
  if (!lastSyncedAt) return 'Never synced';
  const ms = Date.now() - new Date(lastSyncedAt).getTime();
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  if (minutes < 1) return 'Last sync just now';
  if (minutes < 60) return `Last sync ${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Last sync ${hours}h ago`;
  return `Last sync ${Math.floor(hours / 24)}d ago`;
}

export const SourceCard: React.FC<{
  source: IntakeSource;
  onPress?: () => void;
}> = ({ source, onPress }) => {
  const content = (
    <Card variant="default">
      <View style={styles.row}>
        <Icon name={KIND_ICONS[source.kind]} color="brand" />
        <View style={styles.body}>
          <Text variant="body">{source.name}</Text>
          <Spacer size={1} />
          <Text variant="caption" color="tertiary">
            {KIND_LABELS[source.kind]} · {lastSyncLabel(source.lastSyncedAt)}
          </Text>
        </View>
        <SourceHealthPill health={source.health} />
      </View>
    </Card>
  );
  return onPress ? <Pressable onPress={onPress}>{content}</Pressable> : content;
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  body: { flex: 1, marginLeft: 12, marginRight: 8 },
});
