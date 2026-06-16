import React from 'react';
import {
  Text as RNText,
  type TextStyle,
  type TextProps as RNTextProps,
} from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import type { TextVariant } from '../tokens';

export interface TextProps extends Omit<RNTextProps, 'style'> {
  variant?: TextVariant;
  color?: 'primary' | 'secondary' | 'tertiary' | 'inverse' | 'brand' | 'danger';
  align?: 'auto' | 'left' | 'center' | 'right';
  style?: TextStyle | TextStyle[];
  children: React.ReactNode;
}

/**
 * Typography primitive — the only way text renders in the app.
 * Direct fontSize / fontWeight at call sites is rejected by lint.
 */
export const Text: React.FC<TextProps> = ({
  variant = 'body',
  color = 'primary',
  align = 'auto',
  style,
  children,
  ...rest
}) => {
  const t = useTheme();
  const variantStyle = t.typography[variant];
  const resolvedColor =
    color === 'brand'
      ? t.colors.accent.teal
      : color === 'danger'
        ? t.colors.semantic.danger
        : t.colors.text[color];

  return (
    <RNText
      style={[
        variantStyle,
        { color: resolvedColor, textAlign: align },
        ...(Array.isArray(style) ? style : style ? [style] : []),
      ]}
      {...rest}
    >
      {children}
    </RNText>
  );
};
