import React, { useMemo } from 'react';
import { ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Card, Screen, Skeleton, Spacer, Text } from '@oryx/design-system';
import { SourceCard } from '../components/SourceCard';
import { useIntakeSources } from '../hooks/useIntakeSources';
import { useIntakeStatus } from '../hooks/useIntakeStatus';

/** Health rollup: sources needing attention first (§15.3 language rules). */
export const IntakeHealthScreen: React.FC = () => {
  const navigation = useNavigation();
  const sources = useIntakeSources();
  const status = useIntakeStatus();

  const needsAttention = useMemo(
    () =>
      (sources.data ?? []).filter(
        (s) => s.health === 'auth_required' || s.health === 'degraded',
      ),
    [sources.data],
  );
  const healthy = useMemo(
    () => (sources.data ?? []).filter((s) => s.health === 'healthy'),
    [sources.data],
  );

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Health</Text>
        <Spacer size={2} />
        {status.data ? (
          <Text variant="body" color="secondary">
            {status.data.byHealth.healthy} of {status.data.total} sources healthy.
          </Text>
        ) : (
          <Skeleton height={20} />
        )}
        <Spacer size={6} />

        <Text variant="caption" color="tertiary">
          NEEDS ATTENTION
        </Text>
        <Spacer size={2} />
        {needsAttention.length === 0 ? (
          <Card variant="default">
            <Text variant="bodySm" color="secondary">
              Nothing needs attention right now.
            </Text>
          </Card>
        ) : (
          needsAttention.map((s) => (
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

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          HEALTHY
        </Text>
        <Spacer size={2} />
        {healthy.map((s) => (
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
        ))}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
