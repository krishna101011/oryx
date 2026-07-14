import React from 'react';
import { StyleSheet, type TextStyle, View, type ViewStyle } from 'react-native';
import { Icon, Pressable, Spacer, Text, gx } from '@oryx/design-system';
import type { ContentDraft } from '@oryx/shared-types';
import { draftMeta, draftStatusChip, draftUpdatedDate } from '../home';

/** Status tone → gx chip wash, exhaustive on draftStatusChip's tone union. */
function chipToneStyle(
  tone: ReturnType<typeof draftStatusChip>['tone'],
): { chip: ViewStyle | undefined; text: TextStyle } {
  switch (tone) {
    case 'positive':
      return { chip: gx.chipTeal, text: gx.chipTealText };
    case 'warn':
      return { chip: gx.chipWarn, text: gx.chipWarnText };
    case 'negative':
      return { chip: gx.chipNeg, text: gx.chipNegText };
    case 'neutral':
      return { chip: undefined, text: gx.chipText };
  }
}

/**
 * One Content Studio draft row (CS-2 anatomy, design-foundation wave
 * 2026-07-15) — rendered inside the home screen's HairlineRowList, matching
 * the WorkspaceCard/RW-1 row shape. Line 1: fixed-width mono updated-date
 * column (real updatedAt) + status chip; line 2: the title; line 3: the mono
 * meta line (format · word count · version). The reference queue row's
 * channel list (content.jsx "ch" mock) has no backing field on ContentDraft
 * (see ../home.ts's module note) so it is not rendered.
 */
export const DraftCard: React.FC<{
  draft: ContentDraft;
  onPress: () => void;
}> = ({ draft, onPress }) => {
  const chip = draftStatusChip(draft.status);
  const tone = chipToneStyle(chip.tone);
  const updated = draftUpdatedDate(draft);
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={draft.title}
    >
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <View style={styles.head}>
            {updated ? (
              <Text variant="caption" color="tertiary" style={styles.dateCol}>
                {updated}
              </Text>
            ) : null}
            <View style={[gx.chip, tone.chip]}>
              <Text variant="caption" style={tone.text}>
                {chip.label}
              </Text>
            </View>
          </View>
          <Spacer size={1} />
          <Text variant="body">{draft.title}</Text>
          <Spacer size={1} />
          <Text variant="caption" color="tertiary">
            {draftMeta(draft)}
          </Text>
        </View>
        <View style={styles.chevron}>
          <Icon name="ChevronRight" size="sm" color="tertiary" />
        </View>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  head: { flexDirection: 'row', alignItems: 'center', columnGap: 8 },
  // Fixed-width mono timestamp column — the reference queue row's `minWidth: 80`
  // "09:30 ET" slot, ported verbatim onto the real updated-date string.
  dateCol: { minWidth: 80 },
  chevron: { marginTop: 4, marginLeft: 8 },
});
