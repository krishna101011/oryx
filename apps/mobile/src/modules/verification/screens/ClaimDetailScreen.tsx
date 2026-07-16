import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Card,
  Divider,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { EvidenceWithLink } from '@oryx/shared-types';
import type { SettingsStackParamList } from '../../../navigation/types';
import { verificationApi } from '../api/verification';
import { useClaim, useClaimEvidence } from '../hooks/useIntelligence';
import { useReviewClaim } from '../hooks/useReview';
import { ConfidenceMeter } from '../components/ConfidenceMeter';
import { EpistemicTypeBadge } from '../components/EpistemicTypeBadge';

/** Full claim detail with evidence and (when flagged) analyst override. */
export const ClaimDetailScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'ClaimDetail'>>();
  const navigation = useNavigation();
  const theme = useTheme();
  const { claimId } = route.params;

  const claim = useClaim(claimId);
  const evidence = useClaimEvidence(claimId);
  const review = useReviewClaim(claimId);
  const runs = useQuery({
    queryKey: ['verification', 'runs', claimId],
    queryFn: async () => (await verificationApi.runsForClaim(claimId)).data,
  });
  const [note, setNote] = useState('');

  if (claim.isLoading || !claim.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={160} />
      </Screen>
    );
  }
  const c = claim.data;
  const latestScore = runs.data?.[0]?.confidenceScore ?? null;
  const noteEmpty = note.trim().length === 0;

  const act = (outcome: string) =>
    review.mutate({ outcome, note }, { onSuccess: () => navigation.goBack() });

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Claim</Text>
        <Spacer size={3} />
        <Text variant="body">{c.text}</Text>
        <Spacer size={4} />

        <Card variant="elevated">
          <Row label="Subject" value={c.subject} />
          <Divider />
          <Row label="Predicate" value={c.predicate} />
          <Divider />
          <Row label="Object" value={c.object ?? '—'} />
        </Card>

        <Spacer size={4} />
        <EpistemicTypeBadge type={c.epistemicType} />
        <Spacer size={3} />
        <ConfidenceMeter score={latestScore} />

        <Spacer size={6} />
        <Text variant="h2">Evidence</Text>
        <Spacer size={3} />
        {(evidence.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No evidence linked.
          </Text>
        ) : (
          (evidence.data ?? []).map((e: EvidenceWithLink) => (
            <React.Fragment key={e.id}>
              <Card variant="elevated">
                <Text variant="caption" color="secondary">
                  {e.evidenceType} · {e.link.relationship} ·{' '}
                  {Math.round(e.link.strength * 100)}%
                </Text>
                <Spacer size={1} />
                <Text variant="bodySm">{e.text}</Text>
              </Card>
              <Spacer size={2} />
            </React.Fragment>
          ))
        )}

        {c.requiresAnalystReview ? (
          <>
            <Spacer size={6} />
            <Text variant="h2">Analyst review</Text>
            <Spacer size={3} />
            <TextInput
              value={note}
              onChangeText={setNote}
              multiline
              placeholder="Required: explain your decision"
              placeholderTextColor={theme.colors.text.tertiary}
              style={[
                styles.note,
                {
                  borderColor: theme.colors.border.default,
                  color: theme.colors.text.primary,
                },
              ]}
            />
            <Spacer size={3} />
            <Button
              label="Override: Verified"
              variant="primary"
              fullWidth
              disabled={noteEmpty || review.isPending}
              onPress={() => act('override_verified')}
            />
            <Spacer size={2} />
            <Button
              label="Override: Unverified"
              variant="secondary"
              fullWidth
              disabled={noteEmpty || review.isPending}
              onPress={() => act('override_unverified')}
            />
            <Spacer size={2} />
            <Button
              label="Flag"
              variant="secondary"
              fullWidth
              disabled={noteEmpty || review.isPending}
              onPress={() => act('flagged')}
            />
          </>
        ) : null}
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
  note: {
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 80,
    padding: 12,
    textAlignVertical: 'top',
  },
});
