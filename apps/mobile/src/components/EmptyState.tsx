import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Spacer, Text } from '@oryx/design-system';
import { HornMark } from './HornMark';

export interface EmptyStateProps {
  /** Optional brand motif. 'horn' renders the sparing oryx-horn mark. */
  icon?: 'horn';
  title: string;
  description: string;
  ctaLabel?: string;
  onPress?: () => void;
}

/**
 * Shared empty-state block for list screens: an invitation (not an apology),
 * a one-line explanation, and an optional verb-first CTA. The horn motif is the
 * only place HornMark is used in the app.
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
    {icon === 'horn' ? (
      <>
        <HornMark />
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
