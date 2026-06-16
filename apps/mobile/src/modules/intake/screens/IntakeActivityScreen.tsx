import React from 'react';
import { ScrollView } from 'react-native';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Card, Screen, Spacer, Text } from '@oryx/design-system';
import type { SettingsStackParamList } from '../../../navigation/types';
import { SourceCard } from '../components/SourceCard';
import { AuditTimeline } from '../components/AuditTimeline';
import { useIntakeSources } from '../hooks/useIntakeSources';
import { useSourceAudit } from '../hooks/useSourceAudit';

/**
 * Per-source operational audit feed. Without a source param, shows a
 * picker — the audit endpoint is per-source by design (§14.2); there is
 * deliberately no workspace-wide item feed in Phase 3 (§15.3).
 */
export const IntakeActivityScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'IntakeActivity'>>();
  const sourceId = route.params?.sourceId;
  return sourceId ? <SourceAudit sourceId={sourceId} /> : <SourcePicker />;
};

const SourceAudit: React.FC<{ sourceId: string }> = ({ sourceId }) => {
  const audit = useSourceAudit(sourceId);
  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Activity</Text>
        <Spacer size={6} />
        <AuditTimeline
          entries={audit.data?.entries ?? []}
          loading={audit.isLoading}
          hasMore={audit.hasNextPage ?? false}
          onLoadMore={() => audit.fetchNextPage()}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const SourcePicker: React.FC = () => {
  const navigation = useNavigation();
  const sources = useIntakeSources();
  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Activity</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Pick a source to see its operational history.
        </Text>
        <Spacer size={6} />
        {(sources.data ?? []).length === 0 ? (
          <Card variant="default">
            <Text variant="bodySm" color="secondary">
              No sources connected yet.
            </Text>
          </Card>
        ) : (
          (sources.data ?? []).map((s) => (
            <React.Fragment key={s.id}>
              <SourceCard
                source={s}
                onPress={() =>
                  // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
                  navigation.navigate('IntakeActivity', { sourceId: s.id })
                }
              />
              <Spacer size={2} />
            </React.Fragment>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
