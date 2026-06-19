import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Button,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { ContentFormat } from '@oryx/shared-types';
import { usePackets } from '../../research/hooks/useResearch';
import { useGenerateDraft } from '../hooks/useDrafts';
import { CONTENT_FORMATS, FORMAT_LABEL } from '../theme/draftColors';

export const GenerateDraftScreen: React.FC = () => {
  const navigation = useNavigation();
  const theme = useTheme();
  const packets = usePackets();
  const generate = useGenerateDraft();

  const [packetId, setPacketId] = useState<string | null>(null);
  const [format, setFormat] = useState<ContentFormat>('article');
  const [instructions, setInstructions] = useState('');

  const readyPackets = (packets.data ?? []).filter((p) => p.status === 'ready');

  const onGenerate = () => {
    if (!packetId) return;
    generate.mutate(
      {
        packet_id: packetId,
        format,
        instructions: instructions.trim() || null,
      },
      {
        onSuccess: (draft) => {
          // @ts-expect-error param-carrying navigate
          navigation.navigate('DraftEditor', { draftId: draft.id });
        },
      },
    );
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={4} />
        <Text variant="bodySm" color="secondary">
          Ready packet
        </Text>
        <Spacer size={2} />
        {packets.isLoading ? (
          <Skeleton height={80} />
        ) : readyPackets.length === 0 ? (
          <Text variant="bodySm" color="secondary">
            No ready packets. Mark a research packet ready first.
          </Text>
        ) : (
          readyPackets.map((p) => {
            const selected = p.id === packetId;
            return (
              <Pressable key={p.id} onPress={() => setPacketId(p.id)}>
                <View
                  style={[
                    styles.option,
                    {
                      borderColor: selected
                        ? theme.colors.accent.teal
                        : theme.colors.border.subtle,
                    },
                  ]}
                >
                  <Text variant="body">{p.name}</Text>
                  <Text variant="caption" color="tertiary">
                    {p.intelligenceObjectIds.length} objects
                  </Text>
                </View>
              </Pressable>
            );
          })
        )}

        <Spacer size={4} />
        <Text variant="bodySm" color="secondary">
          Format
        </Text>
        <Spacer size={2} />
        <View style={styles.chips}>
          {CONTENT_FORMATS.map((f) => {
            const selected = f === format;
            return (
              <Pressable key={f} onPress={() => setFormat(f)}>
                <View
                  style={[
                    styles.chip,
                    {
                      borderColor: selected
                        ? theme.colors.accent.teal
                        : theme.colors.border.subtle,
                      backgroundColor: selected
                        ? theme.colors.accent.tealGlow
                        : undefined,
                    },
                  ]}
                >
                  <Text
                    variant="caption"
                    color={selected ? 'primary' : 'secondary'}
                  >
                    {FORMAT_LABEL[f]}
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>

        <Spacer size={4} />
        <Text variant="bodySm" color="secondary">
          Instructions (optional)
        </Text>
        <Spacer size={2} />
        <TextInput
          value={instructions}
          onChangeText={setInstructions}
          placeholder="Angle, emphasis, length…"
          placeholderTextColor={theme.colors.text.tertiary}
          multiline
          style={[
            styles.input,
            {
              color: theme.colors.text.primary,
              borderColor: theme.colors.border.subtle,
            },
          ]}
        />

        <Spacer size={4} />
        <Button
          label="Generate with Sonnet"
          variant="primary"
          fullWidth
          loading={generate.isPending}
          disabled={!packetId}
          onPress={onGenerate}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  input: {
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 72,
    padding: 12,
    textAlignVertical: 'top',
  },
  option: { borderRadius: 10, borderWidth: 1, marginBottom: 8, padding: 12 },
});
