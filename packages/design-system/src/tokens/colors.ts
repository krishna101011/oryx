/**
 * Color tokens for ORYX.
 * Source of truth — no component may use a hex value directly.
 * Lint rule enforces this everywhere except inside this folder.
 */
export const colors = {
  bg: {
    // "Midnight Citrus" warm dark ramp (replaces the cool obsidian/navy set).
    primary: '#0D0B08', // obsidian (warm)
    secondary: '#15110A', // navy (warm, recede/secondary)
    card: '#1F1810', // charcoal (warm card surface)
    elevated: '#2A2116', // surface (most elevated)
  },
  text: {
    // Warm-tinted text ramp (replaces the cool grey ramp).
    primary: '#FBF3EA',
    secondary: '#A99884',
    tertiary: '#6E6253',
    inverse: '#0A0A0F',
    // Text-on-fill: dark shade from the SAME family as the fill it sits on,
    // never plain black. Used by buttons/badges over the bright accents.
    onAmber: '#2B1A04',
    onCoral: '#3D1108',
    onTeal: '#04342C',
  },
  accent: {
    // "Midnight Citrus" brand family. amber is the NEW primary (main CTAs,
    // active states); teal is retained (matches the horns logo mark) but now
    // plays a secondary/tertiary role. See SKILL.md — supersedes the prior
    // teal-primary set and the (now-reversed) gold/amber prohibition.
    amber: '#F5A623', // NEW primary
    coral: '#FF6B5C', // secondary
    teal: '#14B8A6', // kept — secondary/tertiary (was #00D4C8)
    tealMuted: '#1A7A7A', // muted teal (disabled/inert ticks)
    tealGlow: 'rgba(20, 184, 166, 0.15)', // selection glow, tracks new teal
    slateBlue: '#4C6EF5', // replaces indigo in decorative/category use
    plum: '#7E5BEF', // replaces violet in decorative/category use
    cream: '#FDE9D9', // subtle light highlight (not a strong fill color)
    brand: '#1A7A7A', // teal mark base (HornMark family) — retained
    brandSecondary: '#1E8F8F', // HornMark stroke — retained
  },
  semantic: {
    success: '#4ADE80',
    warning: '#FBBF24',
    danger: '#F87171',
    info: '#60A5FA',
  },
  border: {
    subtle: 'rgba(255, 255, 255, 0.06)',
    default: 'rgba(255, 255, 255, 0.10)',
    strong: 'rgba(255, 255, 255, 0.18)',
  },
  overlay: {
    scrim: 'rgba(0, 0, 0, 0.60)',
    glass: 'rgba(30, 42, 58, 0.70)',
  },
} as const;

/**
 * Flat ORYX brand palette (brand-spec token names). Components use the
 * structured `colors` object; this is the canonical brand-value reference.
 */
export const oryxPalette = {
  // "Midnight Citrus" — amber primary, warm dark base. brandPrimary/Secondary
  // remain the teal horns-mark values (the logo is unchanged).
  brandPrimary: '#1A7A7A',
  brandSecondary: '#1E8F8F',
  accentAmber: '#F5A623',
  accentCoral: '#FF6B5C',
  accentTeal: '#14B8A6',
  accentSlateBlue: '#4C6EF5',
  accentPlum: '#7E5BEF',
  accentCream: '#FDE9D9',
  baseObsidian: '#0D0B08',
  baseNavy: '#15110A',
  baseCharcoal: '#1F1810',
  baseSurface: '#2A2116',
  textPrimary: '#FBF3EA',
  textSecondary: '#A99884',
  textTertiary: '#6E6253',
} as const;

export type Colors = typeof colors;
export type OryxPalette = typeof oryxPalette;
