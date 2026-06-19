import React, { useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useRoute } from '@react-navigation/native';
import {
  Button,
  Card,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import {
  useDraft,
  useDraftVersions,
  useRegenerateDraft,
  useSaveVersion,
} from '../hooks/useDrafts';
import { FormatBadge } from '../components/FormatBadge';
import { DraftStatusPill } from '../components/DraftStatusPill';
import { CitationTag } from '../components/CitationTag';
import { VersionHistoryList } from '../components/VersionHistoryList';

export const DraftEditorScreen: React.FC = () => {
  const route = useRoute();
  const { draftId } = route.params as { draftId: string };
  const theme = useTheme();

  const draft = useDraft(draftId);
  const versions = useDraftVersions(draftId);
  const save = useSaveVersion(draftId);
  const regen = useRegenerateDraft(draftId);

  const [content, setContent] = useState('');
  const loadedVersion = useRef<number | null>(null);

  // Re-seed the editor whenever a new current version lands (generate,
  // regenerate, or save bumps currentVersion). Edits in between are preserved.
  useEffect(() => {
    const d = draft.data;
    if (!d) return;
    if (loadedVersion.current !== d.currentVersion) {
      setContent(d.currentContent ?? '');
      loadedVersion.current = d.currentVersion;
    }
  }, [draft.data]);

  if (draft.isLoading || !draft.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={220} />
      </Screen>
    );
  }

  const d = draft.data;
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={4} />
        <View style={styles.headerRow}>
          <FormatBadge format={d.format} />
          <DraftStatusPill status={d.status} />
        </View>
        <Spacer size={2} />
        <Text variant="h2">{d.title}</Text>
        <Spacer size={1} />
        <Text variant="caption" color="tertiary">
          {wordCount} words · v{d.currentVersion} · {d.generationModel}
        </Text>

        <Spacer size={4} />
        <Text variant="bodySm" color="secondary">
          Citations
        </Text>
        <Spacer size={2} />
        <View style={styles.citations}>
          {d.citationObjectIds.length === 0 ? (
            <Text variant="caption" color="tertiary">
              No citations.
            </Text>
          ) : (
            d.citationObjectIds.map((id) => (
              <CitationTag key={id} label={id.slice(0, 8)} />
            ))
          )}
        </View>

        <Spacer size={4} />
        <TextInput
          value={content}
          onChangeText={setContent}
          multiline
          placeholder="Draft content…"
          placeholderTextColor={theme.colors.text.tertiary}
          style={[
            styles.editor,
            {
              color: theme.colors.text.primary,
              borderColor: theme.colors.border.subtle,
            },
          ]}
        />

        <Spacer size={4} />
        <Button
          label="Save version"
          variant="primary"
          fullWidth
          loading={save.isPending}
          disabled={!content.trim()}
          onPress={() => save.mutate({ content })}
        />
        <Spacer size={2} />
        <Button
          label="Regenerate with AI"
          variant="secondary"
          fullWidth
          loading={regen.isPending}
          onPress={() => regen.mutate({})}
        />

        <Spacer size={6} />
        <Text variant="bodySm" color="secondary">
          Version history
        </Text>
        <Spacer size={2} />
        <Card variant="elevated">
          <VersionHistoryList versions={versions.data ?? []} />
        </Card>
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  citations: { flexDirection: 'row', flexWrap: 'wrap' },
  editor: {
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 220,
    padding: 12,
    textAlignVertical: 'top',
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
});
