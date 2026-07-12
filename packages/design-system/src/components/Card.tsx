import React, { useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, View, type ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { withAlpha } from '../tokens/colors';
import { useTheme } from '../theme/ThemeProvider';

export type CardVariant = 'default' | 'elevated' | 'glass';

export interface CardProps {
  children: React.ReactNode;
  variant?: CardVariant;
  /**
   * Optional full-bleed header strip rendered above the padded body — pass a
   * <CardHeader/> here so its bottom border spans the card edge-to-edge
   * (the reference .card-head sits outside .card-body's padding).
   */
  header?: React.ReactNode;
  style?: ViewStyle;
  testID?: string;
}

/**
 * Card primitive — the only sanctioned surface for grouped content.
 *
 * Density and border follow the reference .card exactly (styles.css:305-319):
 * 12px body padding, 1px `--border` #1A2330 (border.default — NOT the 4%-white
 * hairline, which is for in-card row separators), radius 6. Cards are FLAT:
 * the reference has no card shadow language (see tokens/shadows.ts note), so
 * `elevated` differs by surface step only (--elev background).
 *
 * `glass` is reserved for overlays (modals, floating headers).
 * Never use it on dense content lists — kills readability.
 */
export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  header,
  style,
  testID,
}) => {
  const t = useTheme();
  const [hovered, setHovered] = useState(false);
  const viewRef = useRef<View>(null);

  // Attach mouse enter/leave to the DOM node on web — RNW View refs are HTMLElements
  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const el = viewRef.current as unknown as HTMLElement | null;
    if (!el) return;
    const onEnter = () => setHovered(true);
    const onLeave = () => setHovered(false);
    el.addEventListener('mouseenter', onEnter);
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mouseenter', onEnter);
      el.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  const base: ViewStyle = {
    borderRadius: t.radius.lg,
    borderWidth: 1,
    borderColor: t.colors.border.default,
  };
  // Padding lives on an inner body view so a `header` can run full-bleed.
  const body = (
    <View style={{ padding: t.spacing[3] }}>{children}</View>
  );

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
        {header}
        {body}
      </BlurView>
    );
  }

  const bg =
    variant === 'elevated' ? t.colors.bg.elevated : t.colors.bg.card;

  // Web-only: smooth transition base (enables animated exit from hover too)
  const webTransition = Platform.OS === 'web' ? ({ transition: 'all 250ms ease' } as ViewStyle) : {};
  // Web-only: glow derived from the teal base (#08314A) at hover opacities
  const webHover =
    Platform.OS === 'web' && hovered
      ? ({
          borderColor: withAlpha(t.colors.accent.teal, 0.22),
          boxShadow: `0 0 16px ${withAlpha(t.colors.accent.teal, 0.18)}`,
        } as ViewStyle)
      : {};

  return (
    <View
      ref={viewRef}
      style={[base, { backgroundColor: bg }, webTransition, webHover, style]}
      testID={testID}
    >
      {header}
      {body}
    </View>
  );
};

// keep StyleSheet import path consistent across primitives
const _styles = StyleSheet.create({});
void _styles;
