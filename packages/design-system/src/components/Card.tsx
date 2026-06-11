import React from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { useTheme } from '../theme/ThemeProvider';

export type CardVariant = 'default' | 'elevated' | 'glass';

export interface CardProps {
  children: React.ReactNode;
  variant?: CardVariant;
  style?: ViewStyle;
  testID?: string;
}

/**
 * Card primitive — the only sanctioned surface for grouped content.
 *
 * `glass` is reserved for overlays (modals, floating headers).
 * Never use it on dense content lists — kills readability.
 */
export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  style,
  testID,
}) => {
  const t = useTheme();
  const base: ViewStyle = {
    borderRadius: t.radius.lg,
    padding: t.spacing[5],
    borderWidth: 1,
    borderColor: t.colors.border.subtle,
  };

  if (variant === 'glass') {
    return (
      <BlurView
        intensity={40}
        tint="dark"
        style={[
          base,
          { backgroundColor: t.colors.overlay.glass, overflow: 'hidden' },
          style,
        ]}
        testID={testID}
      >
        {children}
      </BlurView>
    );
  }

  const bg =
    variant === 'elevated' ? t.colors.bg.elevated : t.colors.bg.card;
  const elevatedShadow: ViewStyle =
    variant === 'elevated'
      ? {
          // Shadows are not themable surfaces; RN shadows are black + opacity by spec.
          // eslint-disable-next-line no-restricted-syntax
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.35,
          shadowRadius: 12,
          elevation: 4,
        }
      : {};

  return (
    <View
      style={[base, { backgroundColor: bg }, elevatedShadow, style]}
      testID={testID}
    >
      {children}
    </View>
  );
};

// keep StyleSheet import path consistent across primitives
const _styles = StyleSheet.create({});
void _styles;
