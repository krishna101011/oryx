/**
 * Border radius tokens — GENSPARK PORT (2026-06-29).
 *
 * The structured scale is remapped to the exact Genspark corner radii so every
 * existing consumer (Card → .card 6px, Button → .btn 5px) picks up the tighter
 * source corners. `gensparkRadius` holds the full named set for new components.
 */
export const radius = {
  none: 0,
  sm: 3, // .tab, .meter, .chip ≈ 3px
  md: 5, // .btn, .cmd, .nav-item, .tab-row, .card-head input ≈ 5px
  lg: 6, // .card, .kpi, .workspace-pill ≈ 6px
  xl: 8, // .nav-badge / pill ≈ 8px
  full: 9999,
} as const;

/** Exact Genspark radii (px), cited to source rules. */
export const gensparkRadius = {
  r2: 2, // .heat-cell, .nav-item.active::before bar, .badge
  r3: 3, // .chip, .meter, .tab
  r4: 4, // .icon-btn, .ws-icon, .nav-badge dot
  r5: 5, // .btn, .cmd, .nav-item
  r6: 6, // .card, .kpi, .workspace-pill
  r8: 8, // .nav-badge pill
  full: 9999, // .avatar, .nav-dot, .status-dot
} as const;

export type Radius = typeof radius;
export type RadiusKey = keyof Radius;
export type GensparkRadius = typeof gensparkRadius;
