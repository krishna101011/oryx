import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Pressable, Spacer, Text } from '@anant/design-system';
import type { EpistemicType, IntelligenceStatus } from '@anant/shared-types';
import { ConfidenceMeter } from './ConfidenceMeter';
import { EpistemicTypeBadge } from './EpistemicTypeBadge';
import { VerificationStatusPill } from './VerificationStatusPill';

/**
 * Compact intelligence-object card. ConfidenceMeter + EpistemicTypeBadge are
 * always co-located and visible. Flat props so it works for full objects and
 * for the lighter object summaries in workspace items.
 */
export const IntelligenceObjectCard: React.FC<{
  headline: string;
  epistemicType: EpistemicType;
  confidenceScore: number | null;
  verificationStatus: IntelligenceStatus;
  note?: string | null;
  onPress?: () => void;
}> = ({ headline, epistemicType, confidenceScore, verificationStatus, note, onPress }) => {
  const body = (
    <Card variant="elevated">
      <View style={styles.head}>
        <Text variant="bodySm" style={styles.headline}>
          {headline}
        </Text>
        <VerificationStatusPill status={verificationStatus} />
      </View>
      <Spacer size={2} />
      <View style={styles.metaRow}>
        <EpistemicTypeBadge type={epistemicType} />
      </View>
      <Spacer size={2} />
      <ConfidenceMeter score={confidenceScore} />
      {note ? (
        <>
          <Spacer size={2} />
          <Text variant="caption" color="secondary">
            {note}
          </Text>
        </>
      ) : null}
    </Card>
  );
  return onPress ? <Pressable onPress={onPress}>{body}</Pressable> : body;
};

const styles = StyleSheet.create({
  head: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
  headline: {
    flex: 1,
  },
  metaRow: {
    flexDirection: 'row',
  },
});
