import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Icon, Spacer, Text } from '@anant/design-system';
import { usePacketReadiness } from '../hooks/useResearch';

/**
 * Renders the packet readiness gate result. Red blocker list when not ready,
 * green confirmation when ready. The same gate is enforced server-side
 * (mark-ready returns 409) — this is the analyst-facing mirror of it.
 */
export const PacketReadinessChecker: React.FC<{ packetId: string }> = ({
  packetId,
}) => {
  const readiness = usePacketReadiness(packetId);
  if (readiness.isLoading || !readiness.data) {
    return null;
  }
  const { isReady, blockers } = readiness.data;

  if (isReady) {
    return (
      <Card variant="elevated">
        <View style={styles.row}>
          <Icon name="CircleCheck" color="gold" />
          <Text variant="bodySm" color="gold">
            Ready to publish
          </Text>
        </View>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <View style={styles.row}>
        <Icon name="TriangleAlert" color="danger" />
        <Text variant="bodySm" color="danger">
          {blockers.length} blocker{blockers.length === 1 ? '' : 's'}
        </Text>
      </View>
      <Spacer size={2} />
      {blockers.map((b, i) => (
        <Text key={i} variant="caption" color="danger">
          • {b}
        </Text>
      ))}
    </Card>
  );
};

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
});
