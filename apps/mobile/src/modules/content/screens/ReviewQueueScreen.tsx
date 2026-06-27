import React from 'react';
import { ScrollView, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Screen, Skeleton, Spacer, Text } from '@oryx/design-system';
import { useReviewQueue } from '../hooks/useDrafts';
import { DraftCard } from '../components/DraftCard';
import { EmptyState } from '../../../components/EmptyState';

/**
 * Phase 5 Wave C — drafts awaiting review. Distinct from the verification
 * module's VerificationQueueScreen (claims/conflicts); this lists in-review
 * content drafts via the Wave A filtered-list endpoint (no dedicated queue
 * endpoint). Tap a card → DraftEditorScreen, where the reviewer actions live.
 */
export const ReviewQueueScreen: React.FC = () => {
  const navigation = useNavigation();
  const queue = useReviewQueue();
  const drafts = queue.data ?? [];

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Review queue</Text>
        <Spacer size={2} />
        <Text variant="bodySm" color="secondary">
          Drafts submitted for review. Approve, reject, or request changes.
        </Text>

        <Spacer size={6} />
        {queue.isLoading ? (
          <Skeleton height={100} />
        ) : drafts.length === 0 ? (
          <EmptyState
            title="Nothing pending review"
            description="Drafts submitted for review show up here, ready to approve or send back."
          />
        ) : (
          drafts.map((d) => (
            <View key={d.id}>
              <DraftCard
                draft={d}
                onPress={() =>
                  // @ts-expect-error param-carrying navigate within content stack
                  navigation.navigate('DraftEditor', { draftId: d.id })
                }
              />
              <Spacer size={2} />
            </View>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
