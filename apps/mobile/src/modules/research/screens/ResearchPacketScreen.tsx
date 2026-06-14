import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useRoute } from '@react-navigation/native';
import {
  Button,
  Screen,
  Skeleton,
  Spacer,
  Text,
} from '@anant/design-system';
import type { ResearchStackParamList } from '../../../navigation/types';
import { IntelligenceObjectCard } from '../../verification/components/IntelligenceObjectCard';
import { packetStatusColor } from '../../verification/components/statusColors';
import { useIntelligenceObjects } from '../../verification/hooks/useIntelligence';
import { PacketReadinessChecker } from '../components/PacketReadinessChecker';
import { useMarkReady, usePacket, usePacketReadiness } from '../hooks/useResearch';

export const ResearchPacketScreen: React.FC = () => {
  const route = useRoute<RouteProp<ResearchStackParamList, 'ResearchPacket'>>();
  const { packetId } = route.params;

  const packet = usePacket(packetId);
  const readiness = usePacketReadiness(packetId);
  const markReady = useMarkReady(packetId);
  const allObjects = useIntelligenceObjects({});

  if (packet.isLoading || !packet.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={160} />
      </Screen>
    );
  }
  const p = packet.data;
  const objectIds = new Set(p.intelligenceObjectIds);
  const objects = (allObjects.data ?? []).filter((o) => objectIds.has(o.id));
  const hasBlockers = readiness.data ? !readiness.data.isReady : true;
  const isReady = p.status === 'ready';

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <View style={styles.head}>
          <Text variant="display" style={styles.title}>
            {p.name}
          </Text>
          <View style={[styles.pill, { backgroundColor: packetStatusColor(p.status) }]}>
            <Text variant="caption" color="inverse">
              {p.status}
            </Text>
          </View>
        </View>

        <Spacer size={5} />
        <PacketReadinessChecker packetId={packetId} />

        <Spacer size={5} />
        <Text variant="h2">Objects</Text>
        <Spacer size={3} />
        {objects.length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No objects resolved for this packet.
          </Text>
        ) : (
          objects.map((o) => (
            <View key={o.id}>
              <IntelligenceObjectCard
                headline={o.headline}
                epistemicType={o.epistemicType}
                confidenceScore={o.confidenceScore}
                verificationStatus={o.verificationStatus}
              />
              <Spacer size={2} />
            </View>
          ))
        )}

        <Spacer size={6} />
        <Button
          label={isReady ? 'Ready' : 'Mark Ready'}
          variant="primary"
          fullWidth
          disabled={isReady || hasBlockers || markReady.isPending}
          onPress={() => markReady.mutate()}
        />
        {hasBlockers && !isReady ? (
          <>
            <Spacer size={2} />
            <Text variant="caption" color="secondary" align="center">
              Resolve the blockers above before marking ready.
            </Text>
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  head: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'space-between',
  },
  title: {
    flex: 1,
  },
  pill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
});
