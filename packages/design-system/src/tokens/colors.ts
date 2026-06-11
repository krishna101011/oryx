/**
 * Color tokens for Anant Capital.
 * Source of truth — no component may use a hex value directly.
 * Lint rule enforces this everywhere except inside this folder.
 */
export const colors = {
  bg: {
    primary: '#0A0A0A',
    secondary: '#121212',
    card: '#181818',
    elevated: '#1F1F1F',
  },
  text: {
    primary: '#FFFFFF',
    secondary: '#A0A0A0',
    tertiary: '#6B6B6B',
    inverse: '#0A0A0A',
  },
  accent: {
    gold: '#D4AF7A',
    goldMuted: '#8C7553',
    goldGlow: 'rgba(212, 175, 122, 0.15)',
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
    glass: 'rgba(31, 31, 31, 0.70)',
  },
} as const;

export type Colors = typeof colors;
