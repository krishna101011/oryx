import React from 'react';
import { View } from 'react-native';
import { Spacer, Text } from '@oryx/design-system';
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
}) => {
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
