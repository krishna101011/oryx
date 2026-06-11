import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, type ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

export interface SkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  radius?: number;
  style?: ViewStyle;
}

/** Loading placeholder — subtle pulse animation. */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 16,
  radius,
  style,
}) => {
  const t = useTheme();
  const pulse = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.6,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0.3,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  return (
    <Animated.View
      style={[
        styles.base,
        {
          width: width as number,
          height,
          borderRadius: radius ?? t.radius.sm,
          backgroundColor: t.colors.bg.elevated,
          opacity: pulse,
        },
        style,
      ]}
    />
  );
};

const styles = StyleSheet.create({
  base: {},
});
