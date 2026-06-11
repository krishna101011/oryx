import React from 'react';
import { View } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import type { SpacingKey } from '../tokens';

export interface SpacerProps {
  size?: SpacingKey;
  axis?: 'vertical' | 'horizontal';
}

/** Pure-layout spacer — never use margin to position. */
export const Spacer: React.FC<SpacerProps> = ({
  size = 4,
  axis = 'vertical',
}) => {
  const t = useTheme();
  const value = t.spacing[size];
  return (
    <View
      style={
        axis === 'vertical' ? { height: value } : { width: value }
      }
    />
  );
};
