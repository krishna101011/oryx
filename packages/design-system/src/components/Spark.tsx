import React from 'react';
import Svg, { Polyline } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/**
 * Sparkline — GENSPARK PORT (primitives.jsx <Spark/>).
 *
 * Same min/max normalisation and point math as the source. The positive
 * stroke is a gain DATA MARK, so it takes semantic.positiveText (2026-07-05
 * teal retirement — the #08314A surface tone is illegible as a 1px stroke);
 * `.spark.neg` stays semantic.danger.
 */
export const Spark: React.FC<{
  data: number[];
  width?: number;
  height?: number;
  pos?: boolean;
  /**
   * The reference KPI micro-spark mode (primitives.jsx:58, .kpi .micro
   * styles.css:372): stretch to the parent's full width — Svg width 100%
   * over a normalized 0–100 viewBox with preserveAspectRatio "none" — instead
   * of a fixed pixel width. `width` is ignored in this mode.
   */
  fullWidth?: boolean;
}> = ({ data, width = 60, height = 18, pos = true, fullWidth = false }) => {
  const t = useTheme();
  if (!data || data.length === 0) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const spanX = fullWidth ? 100 : width;
  const points = data
    .map(
      (v, i) =>
        `${(i / (data.length - 1)) * spanX},${
          height - ((v - min) / range) * (height - 2) - 1
        }`,
    )
    .join(' ');
  return (
    <Svg
      width={fullWidth ? '100%' : width}
      height={height}
      viewBox={`0 0 ${spanX} ${height}`}
      preserveAspectRatio={fullWidth ? 'none' : undefined}
    >
      <Polyline
        points={points}
        fill="none"
        stroke={pos ? t.colors.semantic.positiveText : t.colors.semantic.danger}
        strokeWidth={1}
      />
    </Svg>
  );
};
