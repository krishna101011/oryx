import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useRoute } from '@react-navigation/native';
import { Card, Divider, Screen, Skeleton, Spacer, Text } from '@anant/design-system';
import type { SettingsStackParamList } from '../../../navigation/types';
import { useSourceCredibility } from '../hooks/useSourceCredibility';

/**
 * Read-only credibility for one intake source (ADR-031). Accuracy evolves
 * from verification outcomes; it is never edited here. A source with no
 * verified claims yet has no record — we show an empty state, not an error.
 */
export const SourceCredibilityScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'SourceCredibility'>>();
  const { sourceId } = route.params;
  const credibility = useSourceCredibility(sourceId);

  if (credibility.isLoading) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={160} />
      </Screen>
    );
  }

  const c = credibility.data;

  if (!c) {
    return (
      <Screen background="primary">
        <ScrollView showsVerticalScrollIndicator={false}>
          <Spacer size={6} />
          <Text variant="display">Credibility</Text>
          <Spacer size={3} />
          <Text variant="body" color="secondary">
            No credibility data yet. This source hasn&apos;t produced a verified
            claim, so it has no track record to score.
          </Text>
          <Spacer size={8} />
        </ScrollView>
      </Screen>
    );
  }

  const accuracyPct = `${Math.round(c.accuracyRate * 100)}%`;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Credibility</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          How reliably this source&apos;s claims have verified over time.
        </Text>
        <Spacer size={6} />

        <Card variant="elevated">
          <View style={styles.accuracy}>
            <Text variant="display">{accuracyPct}</Text>
            <Text variant="bodySm" color="secondary">
              accuracy rate
            </Text>
          </View>
        </Card>

        <Spacer size={4} />

        <Card variant="elevated">
          <Row label="Verified claims" value={String(c.verifiedClaimCount)} />
          <Divider />
          <Row label="Contested claims" value={String(c.contestedClaimCount)} />
          <Divider />
          <Row label="Total claims" value={String(c.totalClaimCount)} />
          <Divider />
          <Row
            label="Last evaluated"
            value={
              c.lastEvaluatedAt
                ? new Date(c.lastEvaluatedAt).toLocaleString()
                : 'Never'
            }
          />
          <Divider />
          <Row label="Updated" value={new Date(c.updatedAt).toLocaleString()} />
        </Card>

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
  accuracy: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
});
