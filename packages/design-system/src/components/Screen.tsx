import React from 'react';
import { StatusBar, StyleSheet, View, type ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';

export interface ScreenProps {
  children: React.ReactNode;
  /** Use 'secondary' for sectioned scroll backgrounds. */
  background?: 'primary' | 'secondary';
  /** Apply minimum horizontal padding from the design system (default true). */
  padded?: boolean;
  style?: ViewStyle;
  testID?: string;
}

/**
 * Top-level container for every screen.
 * Applies background tokens, safe area handling, and the canonical horizontal padding.
 */
export const Screen: React.FC<ScreenProps> = ({
  children,
  background = 'primary',
  padded = true,
  style,
  testID,
}) => {
  const t = useTheme();
  const bg = t.colors.bg[background];
  return (
    <SafeAreaView
      style={[styles.root, { backgroundColor: bg }]}
      testID={testID}
    >
      <StatusBar barStyle="light-content" />
      <View
        style={[
          styles.inner,
          padded && { paddingHorizontal: t.spacing[4] },
          style,
        ]}
      >
        {children}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  root: { flex: 1 },
  inner: { flex: 1 },
});
