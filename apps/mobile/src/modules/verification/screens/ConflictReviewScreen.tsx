import React, { useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import {
  Button,
  Card,
  Divider,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@anant/design-system';
import type { Claim, ConflictType, ResolveConflictRequest } from '@anant/shared-types';
import type { SettingsStackParamList } from '../../../navigation/types';
import { useConflict, useResolveConflict } from '../hooks/useConflict';
import { ConfidenceMeter } from '../components/ConfidenceMeter';
import { EpistemicTypeBadge } from '../components/EpistemicTypeBadge';
import { SeverityPill } from '../components/SeverityPill';
import { SEVERITY_INDIGO } from '../components/severityColors';

const CONFLICT_TYPE_LABEL: Record<ConflictType, string> = {
  direct_contradiction: 'Direct contradiction',
  factual_disagreement: 'Factual disagreement',
  temporal_inconsistency: 'Temporal inconsistency',
  scope_difference: 'Scope difference',
};

/** Side-by-side conflict resolution with a mandatory decision note. */
export const ConflictReviewScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'ConflictReview'>>();
  const navigation = useNavigation();
  const theme = useTheme();
  const { conflictId } = route.params;

  const conflict = useConflict(conflictId);
  const resolve = useResolveConflict(conflictId);
  const [note, setNote] = useState('');

  if (conflict.isLoading || !conflict.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={200} />
      </Screen>
    );
  }

  const c = conflict.data;
  const noteEmpty = note.trim().length === 0;

  const submit = (outcome: ResolveConflictRequest['outcome']) => {
    resolve.mutate(
      { outcome, note },
      { onSuccess: () => navigation.goBack() },
    );
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <View style={styles.headRow}>
          <View style={styles.typePill}>
            <Text variant="caption" color="inverse">
              {CONFLICT_TYPE_LABEL[c.conflictType]}
            </Text>
          </View>
          <SeverityPill severity={c.severity} />
        </View>

        <Spacer size={5} />
        <View style={styles.columns}>
          <ClaimColumn label="Claim A" claim={c.claimA} score={c.claimAScore} />
          <ClaimColumn label="Claim B" claim={c.claimB} score={c.claimBScore} />
        </View>

        <Spacer size={5} />
        <Divider />
        <Spacer size={4} />

        <Text variant="bodySm" color="secondary">
          Decision note
        </Text>
        <Spacer size={2} />
        <TextInput
          value={note}
          onChangeText={setNote}
          multiline
          placeholder="Required: explain your decision"
          placeholderTextColor={theme.colors.text.tertiary}
          style={[
            styles.note,
            { color: theme.colors.text.primary },
          ]}
        />

        <Spacer size={5} />
        <Button
          label="Claim A is correct"
          variant="primary"
          fullWidth
          disabled={noteEmpty || resolve.isPending}
          onPress={() => submit('a_wins')}
        />
        <Spacer size={2} />
        <Button
          label="Claim B is correct"
          variant="primary"
          fullWidth
          disabled={noteEmpty || resolve.isPending}
          onPress={() => submit('b_wins')}
        />
        <Spacer size={2} />
        <Button
          label="Cannot determine"
          variant="secondary"
          fullWidth
          disabled={noteEmpty || resolve.isPending}
          onPress={() => submit('inconclusive')}
        />
        {resolve.isPending ? (
          <>
            <Spacer size={3} />
            <Text variant="caption" color="secondary" align="center">
              Submitting…
            </Text>
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const ClaimColumn: React.FC<{
  label: string;
  claim: Claim;
  score: number | null;
}> = ({ label, claim, score }) => (
  <View style={styles.column}>
    <Card variant="elevated">
      <Text variant="caption" color="secondary">
        {label}
      </Text>
      <Spacer size={2} />
      <Text variant="bodySm">{claim.subject}</Text>
      <Spacer size={1} />
      <Text variant="caption" color="secondary">
        {claim.predicate}
      </Text>
      {claim.object ? (
        <Text variant="caption" color="secondary">
          {claim.object}
        </Text>
      ) : null}
      <Spacer size={2} />
      <EpistemicTypeBadge type={claim.epistemicType} />
      <Spacer size={3} />
      <ConfidenceMeter score={score} />
    </Card>
  </View>
);

const styles = StyleSheet.create({
  headRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
  },
  typePill: {
    alignSelf: 'flex-start',
    backgroundColor: SEVERITY_INDIGO,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  columns: {
    flexDirection: 'row',
    gap: 10,
  },
  column: {
    flex: 1,
  },
  note: {
    borderColor: 'rgba(127,127,127,0.35)',
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 90,
    padding: 12,
    textAlignVertical: 'top',
  },
});
