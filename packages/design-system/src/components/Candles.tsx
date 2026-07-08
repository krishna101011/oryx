import React from 'react';
import Svg, { G, Line, Rect, Text as SvgText } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

export interface Candle {
  o: number;
  h: number;
  l: number;
  c: number;
  v?: number;
}

/**
 * Candlestick chart — GENSPARK PORT (primitives.jsx <Candles/>).
 *
 * Same padding model, same y-scale, same bar/wick/volume math, same
 * current-price marker as the source. Up candles are gain DATA MARKS — they
 * must read against the dark ramp, so they take semantic.positiveText
 * (2026-07-05 teal retirement); down stays semantic.danger, grid
 * border.default, price line accent.coral.
 * <text fontFamily> uses the loaded JetBrains Mono family.
 */
export const Candles: React.FC<{
  data: Candle[];
  width?: number;
  height?: number;
  showGrid?: boolean;
  showVol?: boolean;
}> = ({ data, width = 800, height = 320, showGrid = true, showVol = true }) => {
  const t = useTheme();
  if (!data || data.length === 0) return null;

  const up = t.colors.semantic.positiveText;
  const down = t.colors.semantic.danger;
  const gridStroke = t.colors.border.default; // #1A2330
  const axisHi = t.colors.text.tertiary; // #6B7588
  const axisLo = t.colors.accent.cream; // unused tone fallback
  const priceLine = t.colors.accent.coral; // #8B5CF6
  const mono = 'JetBrainsMono_400Regular';

  const pad = { l: 44, r: 56, t: 8, b: showVol ? 60 : 18 };
  const w = width;
  const h = height;
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const max = Math.max(...data.map((d) => d.h));
  const min = Math.min(...data.map((d) => d.l));
  const range = max - min || 1;
  const y = (v: number) => pad.t + (1 - (v - min) / range) * innerH;
  const cw = innerW / data.length;
  const barW = Math.max(2, cw * 0.62);

  const grid: React.ReactNode[] = [];
  if (showGrid) {
    for (let i = 0; i <= 5; i++) {
      const v = min + (range * i) / 5;
      grid.push(
        <G key={`g${i}`}>
          <Line
            x1={pad.l}
            x2={w - pad.r}
            y1={y(v)}
            y2={y(v)}
            stroke={gridStroke}
            strokeDasharray="2 4"
          />
          <SvgText
            x={w - pad.r + 6}
            y={y(v) + 3}
            fontSize={9}
            fill={axisHi}
            fontFamily={mono}
          >
            {v.toFixed(0)}
          </SvgText>
          <SvgText
            x={pad.l - 6}
            y={y(v) + 3}
            fontSize={9}
            fill={t.colors.text.tertiary}
            fontFamily={mono}
            textAnchor="end"
          >
            {v.toFixed(0)}
          </SvgText>
        </G>,
      );
    }
  }
  void axisLo;

  const maxV = Math.max(...data.map((d) => d.v || 1));
  const volBase = h - 10;
  const volH = 40;
  const lastCandle = data[data.length - 1];
  const last = lastCandle ? lastCandle.c : 0;
  const ly = y(last);

  return (
    <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      {grid}
      {data.map((d, i) => {
        const cx = pad.l + cw * (i + 0.5);
        const isUp = d.c >= d.o;
        const fill = isUp ? up : down;
        const yo = y(d.o);
        const yc = y(d.c);
        const yh = y(d.h);
        const yl = y(d.l);
        const top = Math.min(yo, yc);
        const bh = Math.max(1, Math.abs(yc - yo));
        return (
          <G key={i}>
            <Line x1={cx} x2={cx} y1={yh} y2={yl} stroke={fill} strokeWidth={1} />
            <Rect x={cx - barW / 2} y={top} width={barW} height={bh} fill={fill} opacity={0.85} />
            {showVol && d.v != null && (
              <Rect
                x={cx - barW / 2}
                y={volBase - (d.v / maxV) * volH}
                width={barW}
                height={(d.v / maxV) * volH}
                fill={fill}
                opacity={0.35}
              />
            )}
          </G>
        );
      })}
      {/* current price line + marker */}
      <G>
        <Line x1={pad.l} x2={w - pad.r} y1={ly} y2={ly} stroke={priceLine} strokeDasharray="3 3" />
        <Rect x={w - pad.r + 2} y={ly - 9} width={50} height={18} fill={priceLine} rx={2} />
        <SvgText
          x={w - pad.r + 27}
          y={ly + 4}
          fontSize={10}
          fontFamily="JetBrainsMono_600SemiBold"
          fill={t.colors.text.inverse}
          textAnchor="middle"
        >
          {last.toFixed(0)}
        </SvgText>
      </G>
    </Svg>
  );
};
