import React from 'react';
import { ActivityIndicator, StyleSheet, TouchableOpacity, View } from 'react-native';
import { Text, useTheme } from '@oryx/design-system';
import type { ContentFormat, ContentTemplate } from '@oryx/shared-types';
import { useTemplates } from '../hooks/useTemplates';

interface Props {
  format: ContentFormat;
  selectedId: string | null;
  onSelect: (template: ContentTemplate | null) => void;
}

export const TemplatePicker: React.FC<Props> = ({ format, selectedId, onSelect }) => {
  const theme = useTheme();
  const { templates, loading } = useTemplates(format);

  if (loading) {
    return (
      <View style={styles.loadingRow}>
        <ActivityIndicator size="small" />
        <Text variant="caption" color="secondary" style={styles.loadingLabel}>
          Loading templates…
        </Text>
      </View>
    );
  }

  if (templates.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text variant="caption" color="secondary" style={styles.label}>
        TEMPLATE
      </Text>
      <View style={styles.chips}>
        {templates.map((t) => {
          const isSelected = t.id === selectedId;
          return (
            <TouchableOpacity
              key={t.id}
              style={[
                styles.chip,
                {
                  borderColor: isSelected
                    ? theme.colors.accent.teal
                    : theme.colors.border.default,
                  backgroundColor: isSelected
                    ? theme.colors.accent.tealGlow
                    : 'transparent',
                },
              ]}
              onPress={() => onSelect(isSelected ? null : t)}
              accessibilityRole="radio"
              accessibilityState={{ selected: isSelected }}
            >
              <Text
                variant="caption"
                color={isSelected ? 'primary' : 'secondary'}
              >
                {t.name}
                {t.isDefault ? ' ★' : ''}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: 8,
  },
  label: {
    marginBottom: 6,
    letterSpacing: 0.5,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 6,
  },
  loadingLabel: {
    marginLeft: 6,
  },
});
