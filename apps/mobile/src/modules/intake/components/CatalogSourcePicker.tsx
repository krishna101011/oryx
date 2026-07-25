import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Card, Skeleton, Spacer, Text } from '@oryx/design-system';
import type { SourceCatalogEntry } from '@oryx/shared-types';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import {
  type CatalogActivationMap,
  groupCatalogBySection,
  isCatalogKeyEnabled,
} from '../catalogPicker';

export interface CatalogSourcePickerProps {
  catalog: SourceCatalogEntry[];
  activationMap: CatalogActivationMap;
  onToggle: (key: string) => void;
  /** Keys with a real create/patch call still in flight — shown as busy, not re-pressable. */
  pendingKeys?: ReadonlySet<string>;
  /**
   * True while the real source-catalog query is still in flight. Both real
   * callers pass `catalog={query.data ?? []}`, so without this an in-flight
   * fetch and a genuinely empty catalog were visually identical (nothing
   * rendered either way) — render a generic Skeleton instead.
   */
  isLoading?: boolean;
}

/**
 * The real, categorized source-catalog picker (Crypto / Markets) — shared by
 * TrustedSourcesScreen (Settings) and FocusAndSourcesScreen (onboarding).
 * Every tile press activates/deactivates a REAL intake_sources row via the
 * origin_kind='catalog' path; there is no WorkspaceSource involvement here.
 */
export const CatalogSourcePicker: React.FC<CatalogSourcePickerProps> = ({
  catalog,
  activationMap,
  onToggle,
  pendingKeys,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <View>
        <SkeletonChoiceTile />
        <Spacer size={2} />
        <SkeletonChoiceTile />
        <Spacer size={2} />
        <SkeletonChoiceTile />
      </View>
    );
  }

  const sections = groupCatalogBySection(catalog);

  return (
    <View>
      {sections.map((section) => (
        <View key={section.title}>
          <Text variant="caption" color="tertiary">
            {section.title.toUpperCase()}
          </Text>
          <Spacer size={2} />
          {section.entries.map((entry) => {
            const pending = pendingKeys?.has(entry.key) ?? false;
            return (
              <React.Fragment key={entry.key}>
                <ChoiceTile
                  label={entry.name}
                  description={
                    pending
                      ? 'Updating…'
                      : `Editorial confidence: ${entry.editorialConfidence}`
                  }
                  selected={isCatalogKeyEnabled(activationMap, entry.key)}
                  onPress={() => {
                    if (!pending) onToggle(entry.key);
                  }}
                />
                <Spacer size={2} />
              </React.Fragment>
            );
          })}
          <Spacer size={4} />
        </View>
      ))}
    </View>
  );
};

/**
 * Bespoke — single consumer. Mirrors the real ChoiceTile shape (recon
 * confirmed it doesn't fit the chevron-row family at all): a bordered
 * `Card variant="default"` with a title bar + description bar on the left,
 * and a trailing circular dot matching ChoiceTile's real 18×18 selection
 * indicator exactly.
 */
const SkeletonChoiceTile: React.FC = () => (
  <Card variant="default">
    <View style={styles.row}>
      <View style={{ flex: 1 }}>
        <Skeleton width="55%" height={14} radius={2} />
        <Spacer size={1} />
        <Skeleton width="80%" height={9} radius={2} />
      </View>
      <Skeleton width={18} height={18} radius={9} style={styles.dot} />
    </View>
  </Card>
);

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  dot: { marginLeft: 12 },
});
