import React from 'react';
import { ScrollView, View, StyleSheet } from 'react-native';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Button, Card, Divider, Screen, Skeleton, Spacer, Text } from '@anant/design-system';
import type { SettingsStackParamList } from '../../../navigation/types';
import { SourceHealthPill } from '../components/SourceHealthPill';
import {
  useDeleteSource,
  useIntakeSource,
  usePatchSource,
  useTriggerSync,
} from '../hooks/useIntakeSources';

/** Health, config summary, manual sync, enable/disable, disconnect (§15.1). */
export const SourceDetailScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'IntakeSourceDetail'>>();
  const navigation = useNavigation();
  const { sourceId } = route.params;

  const source = useIntakeSource(sourceId);
  const patch = usePatchSource(sourceId);
  const remove = useDeleteSource(sourceId);
  const sync = useTriggerSync(sourceId);

  if (source.isLoading || !source.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={120} />
      </Screen>
    );
  }
  const s = source.data;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">{s.name}</Text>
        <Spacer size={3} />
        <SourceHealthPill health={s.health} />
        <Spacer size={6} />

        <Card variant="elevated">
          <Row label="Kind" value={s.kind} />
          <Divider />
          <Row
            label="Last sync"
            value={s.lastSyncedAt ? new Date(s.lastSyncedAt).toLocaleString() : 'Never'}
          />
          <Divider />
          <Row label="Consecutive failures" value={String(s.consecutiveFailures)} />
          <Divider />
          <Row label="Enabled" value={s.enabled ? 'Yes' : 'No'} />
        </Card>

        <Spacer size={6} />
        <Button
          label={sync.isPending ? 'Queuing…' : 'Sync now'}
          variant="primary"
          fullWidth
          disabled={sync.isPending || !s.enabled}
          onPress={() => sync.mutate()}
        />
        <Spacer size={2} />
        <Button
          label="View activity"
          variant="secondary"
          fullWidth
          onPress={() =>
            // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
            navigation.navigate('IntakeActivity', { sourceId })
          }
        />
        <Spacer size={2} />
        <Button
          label={s.enabled ? 'Disable' : 'Enable'}
          variant="secondary"
          fullWidth
          disabled={patch.isPending}
          onPress={() => patch.mutate({ enabled: !s.enabled })}
        />
        <Spacer size={2} />
        <Button
          label="Disconnect"
          variant="danger"
          fullWidth
          disabled={remove.isPending}
          onPress={async () => {
            await remove.mutateAsync();
            navigation.goBack();
          }}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const Row: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.row}>
    <Text variant="bodySm" color="secondary">
      {label}
    </Text>
    <Text variant="bodySm">{value}</Text>
  </View>
);

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
});
