import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { useMutation } from '@tanstack/react-query';
import {
  Button,
  Card,
  Divider,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { SettingsStackParamList } from '../../../navigation/types';
import { researchApi } from '../../research/api/research';
import { useResearchWorkspaces } from '../../research/hooks/useResearch';
import { useIntelligenceObject } from '../hooks/useIntelligence';
import { useReviewObject } from '../hooks/useReview';
import { ConfidenceMeter } from '../components/ConfidenceMeter';
import { ConflictWarningBanner } from '../components/ConflictWarningBanner';
import { EpistemicTypeBadge } from '../components/EpistemicTypeBadge';
import { VerificationStatusPill } from '../components/VerificationStatusPill';

interface KeyFact {
  predicate?: string;
  object?: string | null;
  epistemicType?: string;
  confidence?: number | null;
}

export const IntelligenceObjectDetailScreen: React.FC = () => {
  const route =
    useRoute<RouteProp<SettingsStackParamList, 'IntelligenceObjectDetail'>>();
  const navigation = useNavigation();
  const theme = useTheme();
  const { objectId } = route.params;

  const object = useIntelligenceObject(objectId);
  const review = useReviewObject(objectId);
  const workspaces = useResearchWorkspaces();
  const addItem = useMutation({
    mutationFn: (rwsId: string) =>
      researchApi.addItem(rwsId, { intelligence_object_id: objectId }),
  });
  const [note, setNote] = useState('');
  const [showFacts, setShowFacts] = useState(false);

  if (object.isLoading || !object.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={200} />
      </Screen>
    );
  }
  const o = object.data;
  const facts = o.keyFacts as Record<string, KeyFact>;
  const noteEmpty = note.trim().length === 0;
  const act = (outcome: 'approved' | 'rejected' | 'flagged') =>
    review.mutate({ outcome, note });

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">{o.headline}</Text>
        <Spacer size={3} />
        <View style={styles.metaRow}>
          <VerificationStatusPill status={o.verificationStatus} />
          <EpistemicTypeBadge type={o.epistemicType} />
        </View>
        <Spacer size={3} />
        {/* ConfidenceMeter is always visible, co-located with the badge. */}
        <ConfidenceMeter score={o.confidenceScore} />

        {o.verificationStatus === 'contested' ? (
          <>
            <Spacer size={4} />
            <ConflictWarningBanner />
          </>
        ) : null}

        <Spacer size={4} />
        <Pressable onPress={() => setShowFacts((v) => !v)}>
          <Text variant="bodySm" color="brand">
            {showFacts ? 'Hide' : 'Show'} factor breakdown
          </Text>
        </Pressable>
        {showFacts ? (
          <>
            <Spacer size={2} />
            <Card variant="elevated">
              <Row label="Scoring version" value={String(o.scoringVersion)} />
              <Divider />
              <Row label="Claims" value={String(o.claimIds.length)} />
              <Divider />
              <Row label="Conflicts" value={String(o.conflictIds.length)} />
            </Card>
          </>
        ) : null}

        <Spacer size={6} />
        <Text variant="h2">Claims</Text>
        <Spacer size={3} />
        {o.claimIds.map((cid) => (
          <React.Fragment key={cid}>
            <Pressable
              onPress={() =>
                // @ts-expect-error param-carrying navigate; typed via SettingsStackParamList
                navigation.navigate('ClaimDetail', { claimId: cid })
              }
            >
              <Card variant="elevated">
                <Text variant="bodySm">Claim {cid.slice(0, 8)}</Text>
              </Card>
            </Pressable>
            <Spacer size={2} />
          </React.Fragment>
        ))}

        <Spacer size={4} />
        <Text variant="h2">Key facts</Text>
        <Spacer size={3} />
        <Card variant="elevated">
          {Object.entries(facts).map(([subject, f], i) => (
            <React.Fragment key={subject}>
              {i > 0 ? <Divider /> : null}
              <View style={styles.fact}>
                <Text variant="bodySm">{subject}</Text>
                <Text variant="caption" color="secondary">
                  {f.predicate} {f.object ?? ''}
                </Text>
              </View>
            </React.Fragment>
          ))}
        </Card>

        <Spacer size={6} />
        <Text variant="h2">Analyst actions</Text>
        <Spacer size={3} />
        <TextInput
          value={note}
          onChangeText={setNote}
          multiline
          placeholder="Required: explain your decision"
          placeholderTextColor={theme.colors.text.tertiary}
          style={[styles.note, { color: theme.colors.text.primary }]}
        />
        <Spacer size={3} />
        <Button
          label="Approve"
          variant="primary"
          fullWidth
          disabled={noteEmpty || review.isPending}
          onPress={() => act('approved')}
        />
        <Spacer size={2} />
        <Button
          label="Reject"
          variant="danger"
          fullWidth
          disabled={noteEmpty || review.isPending}
          onPress={() => act('rejected')}
        />
        <Spacer size={2} />
        <Button
          label="Flag for review"
          variant="secondary"
          fullWidth
          disabled={noteEmpty || review.isPending}
          onPress={() => act('flagged')}
        />

        <Spacer size={6} />
        <Text variant="h2">Add to research workspace</Text>
        <Spacer size={3} />
        {(workspaces.data ?? []).length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No research workspaces yet.
          </Text>
        ) : (
          (workspaces.data ?? []).map((w) => (
            <React.Fragment key={w.id}>
              <Button
                label={w.name}
                variant="secondary"
                fullWidth
                disabled={addItem.isPending}
                onPress={() => addItem.mutate(w.id)}
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

const Row: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.row}>
    <Text variant="bodySm" color="secondary">
      {label}
    </Text>
    <Text variant="bodySm">{value}</Text>
  </View>
);

const styles = StyleSheet.create({
  metaRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  fact: {
    paddingVertical: 8,
  },
  note: {
    borderColor: 'rgba(127,127,127,0.35)',
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 80,
    padding: 12,
    textAlignVertical: 'top',
  },
});
