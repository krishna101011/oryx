import React from 'react';
import { ScrollView, View, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Button, Card, Screen, Skeleton, Spacer, Text } from '@anant/design-system';
import { useMe } from '../../../hooks/useMe';
import { SourceCard } from '../components/SourceCard';
import { useIntakeSources } from '../hooks/useIntakeSources';
import { useIntakeStatus } from '../hooks/useIntakeStatus';

/**
 * Sources dashboard (§15.1). Operational state only — no item lists,
 * no content surfacing (§15.3).
 */
export const IntakeHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const me = useMe();
  const sources = useIntakeSources();
  const status = useIntakeStatus();

  const showManualIngest =
    (me.data?.account.isPlatformAdmin ?? false) &&
    (me.data?.flags.ff_intake_manual ?? false);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="gold">
          INTAKE
        </Text>
        <Spacer size={2} />
        <Text variant="display">Sources</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Everything feeding your pipeline, in one place.
        </Text>
        <Spacer size={6} />

        {status.data ? (
          <Card variant="elevated">
            <View style={styles.statsRow}>
              <Stat label="Connected" value={status.data.total} />
              <Stat label="Healthy" value={status.data.byHealth.healthy} />
              <Stat label="Degraded" value={status.data.byHealth.degraded} />
              <Stat label="Auth" value={status.data.byHealth.auth_required} />
            </View>
          </Card>
        ) : (
          <Skeleton height={72} />
        )}

        <Spacer size={4} />
        <View style={styles.actionsRow}>
          <View style={styles.actionButton}>
            <Button
              label="Manage"
              variant="secondary"
              fullWidth
              onPress={() => navigation.navigate('IntakeSourceManagement' as never)}
            />
          </View>
          <View style={styles.actionButton}>
            <Button
              label="Health"
              variant="secondary"
              fullWidth
              onPress={() => navigation.navigate('IntakeHealth' as never)}
            />
          </View>
        </View>

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          CONNECTED SOURCES
        </Text>
        <Spacer size={2} />
        {sources.isLoading ? (
          <>
            <Skeleton height={64} />
            <Spacer size={2} />
            <Skeleton height={64} />
          </>
        ) : (sources.data ?? []).length === 0 ? (
          <Card variant="default">
            <Text variant="body" color="secondary">
              No sources connected yet. Add your first feed from Manage.
            </Text>
          </Card>
        ) : (
          (sources.data ?? []).map((s) => (
            <React.Fragment key={s.id}>
              <SourceCard
                source={s}
                onPress={() =>
                  // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
                  navigation.navigate('IntakeSourceDetail', { sourceId: s.id })
                }
              />
              <Spacer size={2} />
            </React.Fragment>
          ))
        )}

        {showManualIngest ? (
          <>
            <Spacer size={6} />
            <Text variant="caption" color="tertiary">
              OPERATOR TOOLS
            </Text>
            <Spacer size={2} />
            <Button
              label="Manual ingest"
              variant="ghost"
              onPress={() => navigation.navigate('ManualIngest' as never)}
            />
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const Stat: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <View style={styles.stat}>
    <Text variant="h1">{String(value)}</Text>
    <Text variant="caption" color="tertiary">
      {label}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  statsRow: { flexDirection: 'row', justifyContent: 'space-between' },
  stat: { alignItems: 'center', flex: 1 },
  actionsRow: { flexDirection: 'row' },
  actionButton: { flex: 1, marginRight: 8 },
});
