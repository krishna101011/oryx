import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Icon, Pressable, Spacer, Text, useGx } from '@oryx/design-system';
import type { ResearchWorkspace } from '@oryx/shared-types';
import { statusChip, workspaceMeta, workspaceRowId } from '../list';

/**
 * One Research Workspace row (RW-1 anatomy, design-foundation wave
 * 2026-07-13) — rendered INSIDE the list screen's HairlineRowList, not as a
 * standalone card anymore. Line 1: mono row id (from the real uuid) + status
 * chip; line 2: the name at the body (12.5px) scale; line 3: real
 * description (if any) and the mono UPDATED meta. Only real fields render —
 * ResearchWorkspace has no claim count or owner display name, so none appear.
 */
export const WorkspaceCard: React.FC<{
  workspace: ResearchWorkspace;
  onPress?: () => void;
}> = ({ workspace, onPress }) => {
  const gx = useGx();
  const chip = statusChip(workspace.status);
  const meta = workspaceMeta(workspace);
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={workspace.name}
    >
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <View style={styles.head}>
            <Text variant="caption" color="tertiary">
              {workspaceRowId(workspace.id)}
            </Text>
            <View style={[gx.chip, chip.tone === 'positive' && gx.chipTeal]}>
              <Text
                variant="caption"
                style={chip.tone === 'positive' ? gx.chipTealText : gx.chipText}
              >
                {chip.label}
              </Text>
            </View>
          </View>
          <Spacer size={1} />
          <Text variant="body">{workspace.name}</Text>
          {workspace.description ? (
            <>
              <Spacer size={1} />
              <Text variant="caption" color="secondary" numberOfLines={2}>
                {workspace.description}
              </Text>
            </>
          ) : null}
          {meta ? (
            <>
              <Spacer size={1} />
              <Text variant="caption" color="tertiary">
                {meta}
              </Text>
            </>
          ) : null}
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
  chevron: { marginTop: 4, marginLeft: 8 },
});
