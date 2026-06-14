import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import {
  Button,
  Card,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
} from '@anant/design-system';
import type { EpistemicType, IntelligenceStatus } from '@anant/shared-types';
import type { ResearchStackParamList } from '../../../navigation/types';
import { IntelligenceObjectCard } from '../../verification/components/IntelligenceObjectCard';
import { packetStatusColor } from '../../verification/components/statusColors';
import {
  useCreatePacket,
  usePackets,
  useResearchWorkspace,
  useWorkspaceItems,
} from '../hooks/useResearch';

export const ResearchWorkspaceDetailScreen: React.FC = () => {
  const route =
    useRoute<RouteProp<ResearchStackParamList, 'ResearchWorkspaceDetail'>>();
  const navigation = useNavigation();
  const { rwsId } = route.params;

  const workspace = useResearchWorkspace(rwsId);
  const items = useWorkspaceItems(rwsId);
  const packets = usePackets();
  const createPacket = useCreatePacket();

  if (workspace.isLoading || !workspace.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={120} />
      </Screen>
    );
  }
  const ws = workspace.data;
  const rwsPackets = (packets.data ?? []).filter(
    (p) => p.researchWorkspaceId === rwsId,
  );
  const objectIds = (items.data ?? [])
    .map((i) => i.object?.id)
    .filter((x): x is string => Boolean(x));

  const onNewPacket = () => {
    createPacket.mutate(
      {
        research_workspace_id: rwsId,
        name: `${ws.name} packet`,
        intelligence_object_ids: objectIds,
      },
      {
        onSuccess: (packet) =>
          // @ts-expect-error param-carrying navigate
          navigation.navigate('ResearchPacket', { packetId: packet.id }),
      },
    );
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">{ws.name}</Text>
        {ws.description ? (
          <>
            <Spacer size={2} />
            <Text variant="body" color="secondary">
              {ws.description}
            </Text>
          </>
        ) : null}

        <Spacer size={5} />
        <Button
          label="Add objects"
          variant="primary"
          fullWidth
          onPress={() =>
            // @ts-expect-error param-carrying navigate
            navigation.navigate('IntelligenceObjectPicker', {
              rwsId,
              workspaceName: ws.name,
            })
          }
        />
        <Spacer size={2} />
        <Button
          label="New packet"
          variant="secondary"
          fullWidth
          disabled={objectIds.length === 0 || createPacket.isPending}
          onPress={onNewPacket}
        />

        <Spacer size={6} />
        <Text variant="h2">Objects</Text>
        <Spacer size={3} />
        {(items.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No objects pinned yet.
          </Text>
        ) : (
          (items.data ?? []).map((item) =>
            item.object ? (
              <View key={item.intelligenceObjectId}>
                <IntelligenceObjectCard
                  headline={item.object.headline}
                  epistemicType={item.object.epistemicType as EpistemicType}
                  confidenceScore={item.object.confidenceScore}
                  verificationStatus={
                    item.object.verificationStatus as IntelligenceStatus
                  }
                  note={item.note}
                  onPress={() =>
                    // @ts-expect-error param-carrying navigate
                    navigation.navigate('IntelligenceObjectDetail', {
                      objectId: item.object!.id,
                    })
                  }
                />
                <Spacer size={2} />
              </View>
            ) : null,
          )
        )}

        <Spacer size={6} />
        <Text variant="h2">Packets</Text>
        <Spacer size={3} />
        {rwsPackets.length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No packets yet.
          </Text>
        ) : (
          rwsPackets.map((p) => (
            <View key={p.id}>
              <Pressable
                onPress={() =>
                  // @ts-expect-error param-carrying navigate
                  navigation.navigate('ResearchPacket', { packetId: p.id })
                }
              >
                <Card variant="elevated">
                  <View style={styles.packetRow}>
                    <Text variant="bodySm">{p.name}</Text>
                    <View
                      style={[
                        styles.pill,
                        { backgroundColor: packetStatusColor(p.status) },
                      ]}
                    >
                      <Text variant="caption" color="inverse">
                        {p.status}
                      </Text>
                    </View>
                  </View>
                  <Spacer size={1} />
                  <Text variant="caption" color="tertiary">
                    {p.intelligenceObjectIds.length} objects
                  </Text>
                </Card>
              </Pressable>
              <Spacer size={2} />
            </View>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  packetRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  pill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
});
