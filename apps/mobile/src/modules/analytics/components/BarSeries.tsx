import React from 'react';
import { type LayoutChangeEvent, View } from 'react-native';
import Svg, { Line, Rect, Text as SvgText } from 'react-native-svg';
import { useTheme } from '@oryx/design-system';

/**
 * Daily time-series bar chart — Phase 7 Wave B.
 *
 * Follows the design-system's Candles/Spark precedent (react-native-svg +
 * theme tokens, no charting dependency): same grid stroke, same JetBrains
 * Mono axis labels, same "data marks must read against the dark ramp" rule —
 * bars take accent.slateBlue (--indigo), the primary solo accent.
 *
 * `data` is dense (zero-padded by the presenter). An all-zero series still
 * renders — flat baseline plus gridlines — so a thin-history chart is never
 * broken, just visibly quiet; the SCREEN decides when to swap in the
 * still-gathering state instead.
 */
export const BarSeries: React.FC<{
  data: number[];
  height?: number;
}> = ({ data, height = 120 }) => {
  const t = useTheme();
  const [width, setWidth] = React.useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  if (!data || data.length === 0) return null;

  const pad = { l: 4, r: 30, t: 6, b: 4 };
  const innerW = Math.max(0, width - pad.l - pad.r);
  const innerH = height - pad.t - pad.b;
  const max = Math.max(...data, 1);
  const slot = data.length > 0 ? innerW / data.length : 0;
  const barW = Math.max(2, slot * 0.6);
  const mono = 'JetBrainsMono_400Regular';

  const gridLines = [0.5, 1].map((f) => {
    const y = pad.t + (1 - f) * innerH;
    return (
      <React.Fragment key={f}>
        <Line
          x1={pad.l}
          x2={width - pad.r}
          y1={y}
          y2={y}
          stroke={t.colors.border.default}
          strokeDasharray="2 4"
        />
        <SvgText
          x={width - pad.r + 4}
          y={y + 3}
          fontSize={9}
          fill={t.colors.text.tertiary}
          fontFamily={mono}
        >
          {Math.round(max * f)}
        </SvgText>
      </React.Fragment>
    );
  });

  return (
    <View onLayout={onLayout} style={{ width: '100%' }}>
      {width > 0 ? (
        <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {gridLines}
          <Line
            x1={pad.l}
            x2={width - pad.r}
            y1={pad.t + innerH}
            y2={pad.t + innerH}
            stroke={t.colors.border.strong}
          />
          {data.map((v, i) => {
            const h = (v / max) * innerH;
            return (
              <Rect
                key={i}
                x={pad.l + slot * i + (slot - barW) / 2}
                y={pad.t + innerH - h}
                width={barW}
                height={h}
                fill={t.colors.accent.slateBlue}
                opacity={0.85}
                rx={1}
              />
            );
          })}
        </Svg>
      ) : null}
    </View>
  );
};
