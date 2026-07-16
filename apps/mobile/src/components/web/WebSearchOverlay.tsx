import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { GensparkIcon, Text, useTheme } from '@oryx/design-system';
import type { IntakeSource, RecentIntakeItem } from '@oryx/shared-types';
import {
  useIntakeSources,
  useRecentIntakeItems,
} from '../../modules/intake/hooks/useIntakeSources';
import { searchWorkspace } from './search';

/**
 * The ⌘K overlay behind the topbar command bar (2026-07-12) — a FIRST, honestly
 * scoped search: connected sources and recent ingested items, the two
 * collections that exist today. Full cross-entity search (claims, drafts,
 * markets) is future scope, and the footer says so instead of faking it.
 *
 * Web-only chrome (rendered by WebShell outside the NavigationContainer), so
 * results navigate through the navigationRef helpers, same as the sidebar.
 */
export const WebSearchOverlay: React.FC<{
  onClose: () => void;
  onOpenSource: (sourceId: string) => void;
  onOpenItem: (itemId: string) => void;
}> = ({ onClose, onOpenSource, onOpenItem }) => {
  const t = useTheme();
  const [query, setQuery] = useState('');

  // The intake module's own hooks — same query keys and cached shapes the
  // Manage Sources and Command Center screens use, so no cache clashes.
  const sources = useIntakeSources();
  const items = useRecentIntakeItems(50);

  // Escape closes — the palette convention the ⌘K affordance promises.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const results = searchWorkspace(query, sources.data ?? [], items.data ?? []);
  const hasQuery = query.trim().length > 0;
  const empty = hasQuery && results.sources.length === 0 && results.items.length === 0;

  return (
    <Pressable
      style={[styles.backdrop, { backgroundColor: t.colors.overlay.scrim }]}
      onPress={onClose}
      accessibilityLabel="Close search"
    >
      {/* Stop backdrop-close from swallowing clicks inside the panel. */}
      <Pressable
        style={[
          styles.panel,
          { backgroundColor: t.colors.bg.card, borderColor: t.colors.border.strong },
        ]}
        onPress={(e) => e.stopPropagation()}
      >
        <View style={[styles.inputRow, { borderBottomColor: t.colors.border.default }]}>
          <GensparkIcon name="Search" size={14} color={t.colors.text.tertiary} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search sources and recent items…"
            placeholderTextColor={t.colors.text.tertiary}
            autoFocus
            style={[styles.input, { color: t.colors.text.primary }]}
            accessibilityLabel="Search"
          />
          <View style={[styles.kbd, { borderColor: t.colors.border.default }]}>
            <Text variant="caption" color="tertiary">esc</Text>
          </View>
        </View>

        <ScrollView style={styles.results} keyboardShouldPersistTaps="handled">
          {!hasQuery ? (
            <View style={styles.hint}>
              <Text variant="bodySm" color="tertiary">
                Type to search your connected sources and recent ingested items.
              </Text>
            </View>
          ) : null}

          {results.sources.length > 0 ? (
            <>
              <View style={styles.groupLabel}>
                <Text variant="navGroup" color="tertiary">SOURCES</Text>
              </View>
              {results.sources.map((s) => (
                <SourceRow key={s.id} source={s} onPress={() => onOpenSource(s.id)} />
              ))}
            </>
          ) : null}

          {results.items.length > 0 ? (
            <>
              <View style={styles.groupLabel}>
                <Text variant="navGroup" color="tertiary">RECENT ITEMS</Text>
              </View>
              {results.items.map((i) => (
                <ItemRow key={i.id} item={i} onPress={() => onOpenItem(i.id)} />
              ))}
            </>
          ) : null}

          {empty ? (
            <View style={styles.hint}>
              <Text variant="bodySm" color="tertiary">
                No matching sources or recent items.
              </Text>
            </View>
          ) : null}
        </ScrollView>

        <View style={[styles.foot, { borderTopColor: t.colors.border.default }]}>
          <Text variant="caption" color="tertiary">
            Searches connected sources and recent items. Claims, drafts and markets search coming later.
          </Text>
        </View>
      </Pressable>
    </Pressable>
  );
};

const SourceRow: React.FC<{ source: IntakeSource; onPress: () => void }> = ({
  source,
  onPress,
}) => {
  const t = useTheme();
  return (
    <Pressable style={styles.resultRow} onPress={onPress}>
      <GensparkIcon name="Inbox" size={13} color={t.colors.text.tertiary} />
      <Text variant="bodySm" color="primary" numberOfLines={1} style={{ flex: 1 }}>
        {source.name}
      </Text>
      <Text variant="caption" color="tertiary">
        {source.kind} · {source.health}
      </Text>
    </Pressable>
  );
};

const ItemRow: React.FC<{ item: RecentIntakeItem; onPress: () => void }> = ({
  item,
  onPress,
}) => {
  const t = useTheme();
  return (
    <Pressable style={styles.resultRow} onPress={onPress}>
      <GensparkIcon name="News" size={13} color={t.colors.text.tertiary} />
      <Text variant="bodySm" color="primary" numberOfLines={1} style={{ flex: 1 }}>
        {item.subject ?? 'Processing…'}
      </Text>
      <Text variant="caption" color="tertiary" numberOfLines={1}>
        {item.sourceName}
      </Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    zIndex: 1000,
  },
  panel: {
    marginTop: 88,
    width: 560,
    maxWidth: '92%',
    maxHeight: 420,
    borderWidth: 1,
    borderRadius: 10,
    overflow: 'hidden',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  input: {
    flex: 1,
    fontSize: 13,
    paddingVertical: 2,
    // RN-web renders a focus outline on text inputs; the panel supplies the frame.
    ...(({ outlineStyle: 'none' } as unknown) as object),
  },
  kbd: {
    borderWidth: 1,
    borderRadius: 3,
    paddingVertical: 1,
    paddingHorizontal: 5,
  },
  results: { flexGrow: 0 },
  groupLabel: { paddingHorizontal: 12, paddingTop: 10, paddingBottom: 4 },
  resultRow: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  hint: { paddingHorizontal: 12, paddingVertical: 14 },
  foot: { paddingHorizontal: 12, paddingVertical: 8, borderTopWidth: 1 },
});
