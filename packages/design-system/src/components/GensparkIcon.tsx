import React from 'react';
import Svg, { Circle, Path, Rect } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/**
 * Genspark icon set — 1:1 PORT of docs/design-reference/icons.jsx.
 *
 * Each entry keeps the exact path data from the source `Icon` map. The source
 * renders 14px stroke icons on a 24×24 viewBox with stroke="currentColor",
 * strokeWidth 1.5, round caps/joins — reproduced here. `color` defaults to the
 * inherited text-secondary token (the source inherits currentColor from CSS).
 *
 * Used by the web sidebar nav + topbar. Native screens keep the lucide-based
 * `Icon` component; these are additive, not a replacement.
 */
export type GensparkIconName =
  | 'Home'
  | 'News'
  | 'Shield'
  | 'Beaker'
  | 'Chart'
  | 'Globe'
  | 'Target'
  | 'Pen'
  | 'Send'
  | 'Zap'
  | 'Bar'
  | 'Book'
  | 'Cpu'
  | 'Users'
  | 'Cog'
  | 'Inbox'
  | 'Search'
  | 'Bell'
  | 'ChevDown'
  | 'ChevRight'
  | 'Plus'
  | 'Dot'
  | 'Sparkles'
  | 'Flag'
  | 'Check'
  | 'X'
  | 'Filter'
  | 'Calendar'
  | 'Lock'
  | 'Eye'
  | 'Mail'
  | 'Rss'
  | 'Webhook'
  | 'Download'
  | 'Upload'
  | 'Play'
  | 'Code'
  | 'Layers';

const sw = 1.5;

/** Path geometry keyed by name (verbatim from icons.jsx). `c` = stroke color. */
function paths(name: GensparkIconName, c: string): React.ReactNode {
  switch (name) {
    case 'Home':
      return (
        <>
          <Path d="M3 11l9-8 9 8" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M5 10v10h14V10" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    case 'News':
      return (
        <>
          <Rect x={3} y={4} width={18} height={16} rx={1.5} stroke={c} strokeWidth={sw} />
          <Path d="M7 8h10M7 12h10M7 16h6" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Shield':
      return (
        <>
          <Path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Path d="M9 12l2 2 4-4" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    case 'Beaker':
      return (
        <>
          <Path d="M9 3v6L4 18a2 2 0 002 3h12a2 2 0 002-3l-5-9V3" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Path d="M9 3h6" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Chart':
      return (
        <>
          <Path d="M3 3v18h18" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M7 14l4-4 3 3 5-6" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    case 'Globe':
      return (
        <>
          <Circle cx={12} cy={12} r={9} stroke={c} strokeWidth={sw} />
          <Path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" stroke={c} strokeWidth={sw} />
        </>
      );
    case 'Target':
      return (
        <>
          <Circle cx={12} cy={12} r={9} stroke={c} strokeWidth={sw} />
          <Circle cx={12} cy={12} r={5} stroke={c} strokeWidth={sw} />
          <Circle cx={12} cy={12} r={1} fill={c} />
        </>
      );
    case 'Pen':
      return <Path d="M4 20l4-1 11-11-3-3L5 16l-1 4z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />;
    case 'Send':
      return (
        <>
          <Path d="M22 2L11 13" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M22 2l-7 20-4-9-9-4 20-7z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
        </>
      );
    case 'Zap':
      return <Path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />;
    case 'Bar':
      return (
        <>
          <Path d="M3 21h18" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Path d="M7 17V9M12 17V5M17 17v-6" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Book':
      return (
        <>
          <Path d="M4 4h12a3 3 0 013 3v14H7a3 3 0 01-3-3V4z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Path d="M4 4v13a3 3 0 003 3" stroke={c} strokeWidth={sw} />
        </>
      );
    case 'Cpu':
      return (
        <>
          <Rect x={5} y={5} width={14} height={14} rx={1.5} stroke={c} strokeWidth={sw} />
          <Rect x={9} y={9} width={6} height={6} stroke={c} strokeWidth={sw} />
          <Path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Users':
      return (
        <>
          <Circle cx={9} cy={8} r={3.5} stroke={c} strokeWidth={sw} />
          <Path d="M2 21c.5-4 3.5-6 7-6s6.5 2 7 6" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Circle cx={17} cy={9} r={2.5} stroke={c} strokeWidth={sw} />
          <Path d="M16 15c3 0 5.5 1.5 6 5" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Cog':
      return (
        <>
          <Circle cx={12} cy={12} r={3} stroke={c} strokeWidth={sw} />
          <Path
            d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"
            stroke={c}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
        </>
      );
    case 'Inbox':
      return (
        <>
          <Path d="M22 12h-6l-2 3h-4l-2-3H2" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M5.5 5h13l3.5 7v6a2 2 0 01-2 2H4a2 2 0 01-2-2v-6L5.5 5z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
        </>
      );
    case 'Search':
      return (
        <>
          <Circle cx={11} cy={11} r={7} stroke={c} strokeWidth={sw} />
          <Path d="M21 21l-4.5-4.5" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Bell':
      return (
        <>
          <Path d="M6 9a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Path d="M10 21a2 2 0 004 0" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'ChevDown':
      return <Path d="M6 9l6 6 6-6" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />;
    case 'ChevRight':
      return <Path d="M9 6l6 6-6 6" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />;
    case 'Plus':
      return <Path d="M12 5v14M5 12h14" stroke={c} strokeWidth={sw} strokeLinecap="round" />;
    case 'Dot':
      return <Circle cx={12} cy={12} r={4} fill={c} />;
    case 'Sparkles':
      return (
        <Path
          d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"
          stroke={c}
          strokeWidth={sw}
          strokeLinecap="round"
        />
      );
    case 'Flag':
      return (
        <>
          <Path d="M4 22V4" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Path d="M4 4h14l-3 5 3 5H4" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
        </>
      );
    case 'Check':
      return <Path d="M5 12l4 4L19 6" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />;
    case 'X':
      return <Path d="M6 6l12 12M18 6L6 18" stroke={c} strokeWidth={sw} strokeLinecap="round" />;
    case 'Filter':
      return <Path d="M3 5h18l-7 9v6l-4-2v-4L3 5z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />;
    case 'Calendar':
      return (
        <>
          <Rect x={3} y={5} width={18} height={16} rx={1.5} stroke={c} strokeWidth={sw} />
          <Path d="M3 10h18M8 3v4M16 3v4" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Lock':
      return (
        <>
          <Rect x={4} y={11} width={16} height={10} rx={1.5} stroke={c} strokeWidth={sw} />
          <Path d="M8 11V7a4 4 0 018 0v4" stroke={c} strokeWidth={sw} />
        </>
      );
    case 'Eye':
      return (
        <>
          <Path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Circle cx={12} cy={12} r={3} stroke={c} strokeWidth={sw} />
        </>
      );
    case 'Mail':
      return (
        <>
          <Rect x={3} y={5} width={18} height={14} rx={1.5} stroke={c} strokeWidth={sw} />
          <Path d="M3 7l9 7 9-7" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
    case 'Rss':
      return (
        <>
          <Path d="M4 11a9 9 0 019 9M4 4a16 16 0 0116 16" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Circle cx={5} cy={19} r={1.5} fill={c} />
        </>
      );
    case 'Webhook':
      return (
        <>
          <Circle cx={6} cy={18} r={3} stroke={c} strokeWidth={sw} />
          <Circle cx={18} cy={18} r={3} stroke={c} strokeWidth={sw} />
          <Circle cx={12} cy={6} r={3} stroke={c} strokeWidth={sw} />
          <Path d="M9 18h6M12 9l-3 6M15 15l-3-6" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Download':
      return (
        <>
          <Path d="M12 3v12" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Path d="M7 10l5 5 5-5" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M3 21h18" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Upload':
      return (
        <>
          <Path d="M12 21V9" stroke={c} strokeWidth={sw} strokeLinecap="round" />
          <Path d="M7 14l5-5 5 5" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
          <Path d="M3 3h18" stroke={c} strokeWidth={sw} strokeLinecap="round" />
        </>
      );
    case 'Play':
      return <Path d="M6 4l14 8-14 8V4z" fill={c} />;
    case 'Code':
      return <Path d="M8 6l-5 6 5 6M16 6l5 6-5 6M14 4l-4 16" stroke={c} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />;
    case 'Layers':
      return (
        <>
          <Path d="M12 3l9 5-9 5-9-5 9-5z" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
          <Path d="M3 13l9 5 9-5M3 18l9 5 9-5" stroke={c} strokeWidth={sw} strokeLinejoin="round" />
        </>
      );
    default:
      return <Circle cx={12} cy={12} r={4} fill={c} />;
  }
}

export const GensparkIcon: React.FC<{
  name: GensparkIconName;
  size?: number;
  color?: string;
}> = ({ name, size = 14, color }) => {
  const t = useTheme();
  const c = color ?? t.colors.text.secondary;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {paths(name, c)}
    </Svg>
  );
};
