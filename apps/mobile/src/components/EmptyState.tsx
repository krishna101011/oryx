import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, OryxMark, Spacer, Text } from '@oryx/design-system';

export interface EmptyStateProps {
  /** Optional brand motif. 'oryx' is preferred; 'horn' remains compatible. */
  icon?: 'horn' | 'oryx';
  title: string;
  description: string;
  ctaLabel?: string;
  onPress?: () => void;
}

/**
 * Shared empty-state block for list screens: an invitation (not an apology),
 * a one-line explanation, and an optional verb-first CTA. The ORYX mark is the
 * shared brand motif for empty states.
 *
 * Typography maps to the six-size token set (no ad-hoc sizes): title → body
 * (16px), description → bodySm (14px, secondary). The CTA reuses the primary
 * Button style.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  ctaLabel,
  onPress,
}) => (
  <View style={styles.wrap}>
    {icon === 'horn' || icon === 'oryx' ? (
      <>
        <OryxMark />
        <Spacer size={4} />
      </>
    ) : null}
    <Text variant="body" align="center">
      {title}
    </Text>
    <Spacer size={2} />
    <Text variant="bodySm" color="secondary" align="center" style={styles.description}>
      {description}
    </Text>
    {ctaLabel && onPress ? (
      <>
        <Spacer size={4} />
        <Button label={ctaLabel} variant="primary" onPress={onPress} />
      </>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  description: {
    maxWidth: 230,
  },
});
