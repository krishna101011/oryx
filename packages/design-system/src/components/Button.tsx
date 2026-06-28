import React from 'react';
import { StyleSheet, View, ActivityIndicator, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Pressable } from './Pressable';
import { Text } from './Text';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
  testID?: string;
}

/**
 * Premium button primitive.
 * Touch target minimum 44pt. Loading state preserves width to avoid layout shift.
 */
export const Button: React.FC<ButtonProps> = ({
  label,
  onPress,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  fullWidth = false,
  style,
  testID,
}) => {
  const t = useTheme();
  const isDisabled = disabled || loading;

  const sizeStyle = {
    sm: { height: 36, paddingHorizontal: t.spacing[4] },
    md: { height: 48, paddingHorizontal: t.spacing[5] },
    lg: { height: 56, paddingHorizontal: t.spacing[6] },
  }[size];

  const variantStyle: ViewStyle = (() => {
    switch (variant) {
      case 'primary':
        // New primary CTA fill is amber; the disabled state is conveyed by the
        // shared opacity treatment below (no separate muted-amber token).
        return { backgroundColor: t.colors.accent.amber };
      case 'secondary':
        return {
          backgroundColor: t.colors.bg.elevated,
          borderWidth: 1,
          borderColor: t.colors.border.default,
        };
      case 'ghost':
        return { backgroundColor: 'transparent' };
      case 'danger':
        return { backgroundColor: t.colors.semantic.danger };
    }
  })();

  const labelColor: React.ComponentProps<typeof Text>['color'] =
    variant === 'primary' ? 'onAmber' : variant === 'danger' ? 'inverse' : 'primary';

  return (
    <Pressable
      onPress={isDisabled ? undefined : onPress}
      disabled={isDisabled}
      animated={!isDisabled}
      testID={testID}
      style={({ pressed }) => [
        styles.base,
        { borderRadius: t.radius.md },
        sizeStyle,
        variantStyle,
        fullWidth && { alignSelf: 'stretch' },
        pressed && !isDisabled && { opacity: 0.92 },
        isDisabled && { opacity: 0.7 },
        style,
      ]}
    >
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator
            color={variant === 'primary' ? t.colors.text.onAmber : t.colors.text.primary}
          />
        ) : (
          <Text variant="body" color={labelColor}>
            {label}
          </Text>
        )}
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  base: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
