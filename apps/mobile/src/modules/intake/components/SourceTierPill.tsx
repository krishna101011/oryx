import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, useTheme } from '@oryx/design-system';
import type { Verification } from '@oryx/shared-types';
import { deriveSourceTier, formatSourceTier } from '../../verification/sourceTier';

/**
 * Source-governance tier + trust score chip (2026-07-22 wave). Mirrors
 * SourceHealthPill's exact dot+label shape and token usage — a DIFFERENT
 * concept (content trust, not sync connectivity) rendered the same way for
 * visual consistency. Color is never the only signal: the label always
 * renders, same rule SourceHealthPill documents.
 *
 * `credibility` is undefined while the workspace-wide credibility list is
 * still loading, or when this source has no record at all yet (a source
 * that has never produced a claim has no row in source_credibility_records —
 * absent, not zero, same discipline as the analytics presenter).
 */
export const SourceTierPill: React.FC<{
  credibility: Verification.SourceCredibility | undefined;
}> = ({ credibility }) => {
  const t = useTheme();
  if (!credibility) return null;
  const tier = deriveSourceTier(credibility.accuracyRate, credibility.totalClaimCount);
  const display = formatSourceTier(tier);
  const dotColor = {
    positive: t.colors.semantic.positiveText,
    danger: t.colors.semantic.danger,
    neutral: t.colors.text.tertiary,
  }[display.tone];
  const trustLabel =
    tier.kind === 'rated' ? `${Math.round(credibility.accuracyRate * 100)}` : null;

  return (
    <View
      style={[
        styles.pill,
        { borderColor: t.colors.border.default, backgroundColor: t.colors.bg.elevated },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: dotColor }]} />
      <Text variant="caption" color="secondary">
        {display.text}
        {trustLabel ? ` · ${trustLabel}` : ''}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
});
