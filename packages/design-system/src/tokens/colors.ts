/**
 * Color tokens for ORYX.
 * Source of truth — no component may use a hex value directly.
 * Lint rule enforces this everywhere except inside this folder.
 */
export const colors = {
  bg: {
    primary: '#0A0A0F', // obsidian
    secondary: '#0F1117', // navy
    card: '#1A2332', // charcoal
    elevated: '#1E2A3A', // surface
  },
  text: {
    primary: '#FFFFFF',
    secondary: '#8B95A5',
    tertiary: '#4E5D6C',
    inverse: '#0A0A0F',
  },
  accent: {
    // ORYX brand mark + UI accent family (replaces the retired gold accents).
    // The `teal*` keys keep the former `gold*` shape so the 'brand' text/icon
    // keyword and the disabled/glow variants resolve without restructuring.
    teal: '#00D4C8',
    tealMuted: '#1A7A7A',
    tealGlow: 'rgba(0, 212, 200, 0.15)',
    brand: '#1A7A7A',
    brandSecondary: '#1E8F8F',
    indigo: '#6366F1',
    violet: '#9B5DE5',
    blue: '#60A5FA',
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
  brandPrimary: '#1A7A7A',
  brandSecondary: '#1E8F8F',
  accentTeal: '#00D4C8',
  accentIndigo: '#6366F1',
  accentViolet: '#9B5DE5',
  accentBlue: '#60A5FA',
  baseObsidian: '#0A0A0F',
  baseNavy: '#0F1117',
  baseCharcoal: '#1A2332',
  baseSurface: '#1E2A3A',
  textPrimary: '#FFFFFF',
  textSecondary: '#8B95A5',
  textTertiary: '#4E5D6C',
} as const;

export type Colors = typeof colors;
export type OryxPalette = typeof oryxPalette;
