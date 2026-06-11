import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Button, Card, Skeleton, Spacer, Text, useTheme } from '@anant/design-system';
import type { IntakeSourceAuditEntry } from '@anant/shared-types';

/** Operational language only (§15.3) — no content, no truth claims. */
const EVENT_LABELS: Record<string, string> = {
  sync_start: 'Sync started',
  sync_complete: 'Sync completed',
  sync_failed: 'Sync failed',
  webhook_received: 'Webhook received',
  dedupe_skip: 'Duplicate skipped',
  circuit_broken: 'Paused after repeated failures',
  circuit_recovered: 'Recovered',
  auth_lapsed: 'Authorization lapsed',
  config_changed: 'Configuration changed',
  rss_permanent_redirect: 'Feed moved (URL updated)',
  gmail_history_expired: 'Re-synced after Gmail history expiry',
  manual_sync_requested: 'Manual sync requested',
  manual_ingest: 'Manual item ingested',
};

export const AuditTimeline: React.FC<{
  entries: IntakeSourceAuditEntry[];
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
}> = ({ entries, loading, hasMore, onLoadMore }) => {
  const t = useTheme();
  if (loading && entries.length === 0) {
    return (
      <View>
        <Skeleton height={56} />
        <Spacer size={2} />
        <Skeleton height={56} />
      </View>
    );
  }
  if (entries.length === 0) {
    return (
      <Card variant="default">
        <Text variant="bodySm" color="secondary">
          No activity recorded yet.
        </Text>
      </Card>
    );
  }
  return (
    <View>
      {entries.map((entry) => (
        <View key={entry.id} style={styles.entryRow}>
          <View style={[styles.tick, { backgroundColor: t.colors.accent.goldMuted }]} />
          <View style={styles.entryBody}>
            <Text variant="bodySm">{EVENT_LABELS[entry.event] ?? entry.event}</Text>
            <Spacer size={1} />
            <Text variant="caption" color="tertiary">
              {new Date(entry.createdAt).toLocaleString()}
            </Text>
          </View>
        </View>
      ))}
      {hasMore ? (
        <>
          <Spacer size={3} />
          <Button label="Load more" variant="ghost" onPress={onLoadMore} />
        </>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  entryRow: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 8 },
  tick: { width: 6, height: 6, borderRadius: 3, marginTop: 6, marginRight: 12 },
  entryBody: { flex: 1 },
});
