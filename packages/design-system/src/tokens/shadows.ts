/**
 * Shadow tokens — GENSPARK PORT (2026-06-29).
 *
 * CSS box-shadow → RN shadow* (iOS) + elevation (Android). RN cannot render an
 * `inset` highlight, so the inset half of --shadow-1 is dropped and only its
 * drop-shadow weight is approximated. Glow shadows (CSS `0 0 6px color`) become
 * a zero-offset colored shadow — the closest faithful equivalent.
 */
const BLACK = '#000000';

export const shadows = {
  // Genspark cards/KPIs are FLAT (border only, no box-shadow). Explicit "no
  // shadow" token so call sites stay declarative.
  none: {
    shadowColor: BLACK,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  // --shadow-1 drop half: 0 8px 24px rgba(0,0,0,0.4)
  elev1: {
    shadowColor: BLACK,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 6,
  },
  // .nav-dot / .status-dot / .ai-btn .pulse glow: box-shadow 0 0 6px <accent>.
  // Colored zero-offset glow; pass the accent via shadowColor at the call site.
  glow: {
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 3,
    elevation: 0,
  },
} as const;

export type Shadows = typeof shadows;
