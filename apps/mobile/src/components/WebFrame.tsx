import React from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { useTheme } from '@oryx/design-system';

/**
 * Web-only presentation frame.
 *
 * On `Platform.OS === 'web'` the app is constrained to a centered, phone-width
 * column (480px) so a desktop browser reads as an intentionally framed mobile
 * surface rather than a stretched/cut-off layout. The gutter outside the column
 * uses the navy base token — a subtle shade off the obsidian app background —
 * so the edge reads as deliberate framing.
 *
 * On iOS/Android this is a pass-through that renders children unchanged: the
 * early return means no extra View, style, or layout is introduced on native.
 */
export const WebFrame: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const t = useTheme();
  if (Platform.OS !== 'web') return <>{children}</>;
  return (
    <View style={[styles.gutter, { backgroundColor: t.colors.bg.secondary }]}>
      <View style={[styles.column, { backgroundColor: t.colors.bg.primary }]}>
        {children}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  gutter: {
    flex: 1,
    alignItems: 'center',
  },
  column: {
    flex: 1,
    maxWidth: 480,
    width: '100%',
  },
});
