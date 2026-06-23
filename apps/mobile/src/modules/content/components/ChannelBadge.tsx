import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text, useTheme } from '@oryx/design-system';
import type { PublishChannel } from '@oryx/shared-types';

export const CHANNEL_LABEL: Record<PublishChannel, string> = {
  twitter_x: 'X',
  linkedin: 'LinkedIn',
  email_newsletter: 'Newsletter',
  notion: 'Notion',
  webhook: 'Webhook',
  export: 'Export',
};

/** Per-channel accent, drawn only from existing design-system tokens. */
function channelColor(channel: PublishChannel, t: ReturnType<typeof useTheme>): string {
  switch (channel) {
    case 'twitter_x':
      return t.colors.accent.blue;
    case 'linkedin':
      return t.colors.accent.indigo;
    case 'notion':
      return t.colors.accent.violet;
    case 'email_newsletter':
      return t.colors.accent.teal;
    case 'webhook':
      return t.colors.accent.brandSecondary;
    default:
      return t.colors.text.tertiary; // export
  }
}

export const ChannelBadge: React.FC<{ channel: PublishChannel }> = ({ channel }) => {
  const t = useTheme();
  return (
    <View style={[styles.badge, { backgroundColor: channelColor(channel, t) }]}>
      <Text variant="caption" color="inverse">
        {CHANNEL_LABEL[channel]}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
});
