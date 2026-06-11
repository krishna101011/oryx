import React, { useCallback } from 'react';
import {
  Pressable as RNPressable,
  type PressableProps as RNPressableProps,
  Animated,
  Easing,
} from 'react-native';

export interface PressableProps extends RNPressableProps {
  /** Apply subtle scale animation on press (default true). */
  animated?: boolean;
}

/**
 * Pressable primitive with consistent feedback.
 * Standardizes touch behavior across the app — never use bare RN Pressable.
 */
export const Pressable: React.FC<PressableProps> = ({
  animated = true,
  children,
  onPressIn,
  onPressOut,
  style,
  ...rest
}) => {
  const scale = React.useRef(new Animated.Value(1)).current;

  const handlePressIn = useCallback(
    (e: Parameters<NonNullable<RNPressableProps['onPressIn']>>[0]) => {
      if (animated) {
        Animated.timing(scale, {
          toValue: 0.97,
          duration: 80,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }).start();
      }
      onPressIn?.(e);
    },
    [animated, onPressIn, scale],
  );

  const handlePressOut = useCallback(
    (e: Parameters<NonNullable<RNPressableProps['onPressOut']>>[0]) => {
      if (animated) {
        Animated.timing(scale, {
          toValue: 1,
          duration: 120,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }).start();
      }
      onPressOut?.(e);
    },
    [animated, onPressOut, scale],
  );

  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <RNPressable
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        style={style}
        {...rest}
      >
        {children as React.ReactNode}
      </RNPressable>
    </Animated.View>
  );
};
