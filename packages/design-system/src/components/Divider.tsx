import React from 'react';
import { View, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

export interface DividerProps {
  variant?: 'subtle' | 'default' | 'strong';
  style?: ViewStyle;
}

export const Divider: React.FC<DividerProps> = ({
  variant = 'default',
  style,
}) => {
  const t = useTheme();
  return (
    <View
      style={[
        { height: 1, backgroundColor: t.colors.border[variant] },
        style,
      ]}
    />
  );
};
