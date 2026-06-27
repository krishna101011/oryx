import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Card,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
} from '@oryx/design-system';
import type { ConflictRecord, ConflictType } from '@oryx/shared-types';
import { useReviewQueue } from '../hooks/useReviewQueue';
import { EpistemicTypeBadge } from '../components/EpistemicTypeBadge';
import { SeverityPill } from '../components/SeverityPill';
import { EmptyState } from '../../../components/EmptyState';

const CONFLICT_TYPE_LABEL: Record<ConflictType, string> = {
  direct_contradiction: 'Direct contradiction',
  factual_disagreement: 'Factual disagreement',
  temporal_inconsistency: 'Temporal inconsistency',
  scope_difference: 'Scope difference',
};

/**
 * Analyst work queue. Section 1 lists claims flagged for review; section 2
 * lists open conflicts, each tappable through to the resolution screen.
 *
 * Note: the queue's open conflicts carry claim IDs, not subjects (the
 * ReviewQueue contract is ConflictRecord[]); the full subjects/scores load on
 * the ConflictReviewScreen. Pending claims are not yet tappable — a
 * ClaimDetailScreen lands in a later wave.
 */
export const VerificationQueueScreen: React.FC = () => {
  const navigation = useNavigation();
  const queue = useReviewQueue();

  if (queue.isLoading || !queue.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={120} />
      </Screen>
    );
  }

  const { pendingClaims, openConflicts } = queue.data;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Review queue</Text>
        <Spacer size={6} />

        {pendingClaims.length === 0 && openConflicts.length === 0 ? (
          <EmptyState
            title="Nothing pending review"
            description="New claims and conflicts will appear here as they're detected."
          />
        ) : (
          <>
        <Text variant="h2">Needs review</Text>
        <Spacer size={3} />
        {pendingClaims.length === 0 ? (
          <Text variant="bodySm" color="secondary">
            Nothing waiting on an analyst.
          </Text>
        ) : (
          pendingClaims.map((claim) => (
            <React.Fragment key={claim.id}>
              <Pressable
                onPress={() =>
                  // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
                  navigation.navigate('ClaimDetail', { claimId: claim.id })
                }
              >
                <Card variant="elevated">
                  <Text variant="bodySm">{claim.subject}</Text>
                  <Spacer size={2} />
                  <Text variant="caption" color="secondary">
                    {claim.text}
                  </Text>
                  <Spacer size={2} />
                  <EpistemicTypeBadge type={claim.epistemicType} />
                </Card>
              </Pressable>
              <Spacer size={2} />
            </React.Fragment>
          ))
        )}

        <Spacer size={6} />
        <Text variant="h2">Open conflicts</Text>
        <Spacer size={3} />
        {openConflicts.length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No open conflicts.
          </Text>
        ) : (
          openConflicts.map((c: ConflictRecord) => (
            <React.Fragment key={c.id}>
              <Pressable
                onPress={() =>
                  // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
                  navigation.navigate('ConflictReview', { conflictId: c.id })
                }
              >
                <Card variant="elevated">
                  <View style={styles.conflictHead}>
                    <Text variant="bodySm">
                      {CONFLICT_TYPE_LABEL[c.conflictType]}
                    </Text>
                    <SeverityPill severity={c.severity} />
                  </View>
                  <Spacer size={2} />
                  <Text variant="caption" color="secondary">
                    Claim {c.claimAId.slice(0, 8)} vs Claim{' '}
                    {c.claimBId.slice(0, 8)} — tap to review
                  </Text>
                </Card>
              </Pressable>
              <Spacer size={2} />
            </React.Fragment>
          ))
        )}
          </>
        )}

        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  conflictHead: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
