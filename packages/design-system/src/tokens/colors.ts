/**
 * Color tokens for ORYX.
 * Source of truth — no component may use a hex value directly.
 * Lint rule enforces this everywhere except inside this folder.
 *
 * ===========================================================================
 * GENSPARK PORT (supersedes "Midnight Citrus", 2026-06-29).
 * Every value below is a 1:1 copy of a `:root` CSS variable in the approved
 * Genspark source (docs/design-reference/styles.css). No value is rounded,
 * approximated, or "improved". The `gensparkPalette` object holds the exact
 * named tokens for traceability; the structured `colors` object maps those
 * same values onto the key shape the app's 100+ call sites already consume,
 * so the visual system changes without touching every screen.
 * Owner-confirmed global brand reversal — see oryx-architect SKILL.md.
 *
 * AMENDMENT (2026-07-05): the teal family (--teal #14B8A6 / --teal-2 #0EA5A0
 * and the --pos gain color) is RETIRED and replaced by the #08314A family.
 * Teal-named KEYS are kept (same convention as amber→indigo) but now hold the
 * new values. #08314A is 1.49:1 against --bg — surface-only. Anything that
 * must READ against the dark ramp (text, numerals, strokes, dots, selected
 * borders) uses `semantic.positiveText`, never `accent.teal`.
 * ===========================================================================
 */

/**
 * Flat Genspark `:root` palette — the canonical brand-value reference.
 * Each entry cites the CSS variable it ports verbatim.
 */
export const gensparkPalette = {
  bg: '#05070A', // --bg
  panel: '#0A0E14', // --panel
  elev: '#10151D', // --elev
  elev2: '#161D28', // --elev-2
  border: '#1A2330', // --border
  borderStrong: '#232F42', // --border-strong
  hairline: 'rgba(255,255,255,0.04)', // --hairline

  text: '#E6EAF2', // --text
  text2: '#A8B0BF', // --text-2
  text3: '#6B7588', // --text-3
  text4: '#4A5263', // --text-4

  indigo: '#5B5BF5', // --indigo
  violet: '#8B5CF6', // --violet
  teal: '#08314A', // --teal (2026-07-05: was #14B8A6 — teal retired)
  teal2: '#041F35', // --teal-2 (derived: the old teal→teal-2 HSL step ΔL −4.9 applied to #08314A)
  softblue: '#60A5FA', // --softblue
  pos: '#08314A', // --pos (2026-07-05: split into semantic.positiveSurface / positiveText)
  neg: '#F87171', // --neg
  warn: '#F59E0B', // --warn
  info: '#60A5FA', // --info

  indigoSoft: '#818cf8', // .chip.indigo text color
  calEventText: '#b5b7ff', // .cal .event color
  onAccent: '#FFFFFF', // .btn.primary color:#fff (text/icon on accent fills)
} as const;

/**
 * Accent gradients. CSS gradient strings have no RN equivalent — ported as
 * start/end color-stop pairs (consumed via expo-linear-gradient). `angle` is
 * the CSS `deg` for documentation; expo-linear-gradient uses start/end points.
 *
 * DECIDED (2026-07-12): the Verification confidence dial reuses `accent`
 * (indigo→violet). The reference draws its dial with a teal→violet gradient
 * (verification.jsx:92-95), but that cross-family pair predates the teal
 * retirement and exists nowhere else — do NOT add a dial gradient here; the
 * future dial component takes `gradients.accent`.
 */
export const gradients = {
  // --accent-grad: linear-gradient(135deg, #5B5BF5 0%, #8B5CF6 100%)
  accent: { from: '#5B5BF5', to: '#8B5CF6', angle: 135 },
  // --accent-grad-soft: linear-gradient(135deg, rgba(91,91,245,0.18), rgba(139,92,246,0.18))
  accentSoft: { from: 'rgba(91,91,245,0.18)', to: 'rgba(139,92,246,0.18)', angle: 135 },
  // sidebar: linear-gradient(180deg, #07090D 0%, #05070A 100%)
  sidebar: { from: '#07090D', to: '#05070A', angle: 180 },
  // .meter-fill.teal: linear-gradient(90deg, var(--teal-2), var(--teal))
  meterTeal: { from: '#041F35', to: '#08314A', angle: 90 },
  // .meter-fill.neg: linear-gradient(90deg, #b45a5a, var(--neg))
  meterNeg: { from: '#b45a5a', to: '#F87171', angle: 90 },
  // .avatar: linear-gradient(135deg, #232F42, #10151D)
  avatar: { from: '#232F42', to: '#10151D', angle: 135 },
} as const;

const g = gensparkPalette;

/**
 * Alpha wash of any token color (2026-07-12; generalizes the old teal-only
 * `tealAlpha`). The single sanctioned way to produce rgba() variants of a
 * token outside this file — keeps chip/badge/hover washes tracking the token
 * instead of hardcoding channel values. Accepts #RRGGBB only, by design: every
 * color token that needs a wash is stored in that form.
 */
export const withAlpha = (color: string, alpha: number): string => {
  const hex = /^#([0-9a-fA-F]{6})$/.exec(color)?.[1];
  if (hex === undefined) {
    throw new Error(`withAlpha expects a #RRGGBB token value, got "${color}"`);
  }
  const n = parseInt(hex, 16);
  return `rgba(${(n >> 16) & 0xff},${(n >> 8) & 0xff},${n & 0xff},${alpha})`;
};

/**
 * Third-party channel identity colors (2026-07-12) — used ONLY to attribute a
 * channel (Analytics attribution rows, Publishing target marks; reference
 * analytics.jsx:113-116, publishing.jsx:3-5). These are external brands' own
 * colors, not ORYX accents: never use them for emphasis, state, or anything
 * except identifying the channel they name.
 */
export const channelColors = {
  substack: '#FF6719',
  linkedin: '#0a66c2',
} as const;

export const colors = {
  bg: {
    // Genspark dark ramp (cool obsidian). bg.secondary == --panel so the
    // WebFrame gutter and recede surfaces read a shade off the app bg.
    primary: g.bg, // --bg   #05070A
    secondary: g.panel, // --panel #0A0E14
    card: g.panel, // --panel #0A0E14 (card/.kpi surface)
    elevated: g.elev, // --elev  #10151D (inputs, .cmd, tab-row)
    elevated2: g.elev2, // --elev-2 #161D28 (.tab.active, .nav-badge)
  },
  text: {
    primary: g.text, // --text   #E6EAF2
    secondary: g.text2, // --text-2 #A8B0BF
    tertiary: g.text3, // --text-3 #6B7588
    inverse: '#FFFFFF', // .btn.primary color: #fff (on accent gradient)
    // Genspark renders white on every accent fill. These keys are retained
    // for the existing Text/Button contract; all resolve to #fff over the
    // bright accent gradient (no same-family dark-on-fill in this system).
    onAmber: '#FFFFFF',
    onCoral: '#FFFFFF',
    onTeal: '#FFFFFF',
  },
  accent: {
    // Genspark accent family. `amber`/`coral` keys are retained (the Button
    // and a few call sites reference them) but now carry the Genspark accent
    // values — indigo→violet is the primary gradient; violet is the solo.
    amber: g.indigo, // PRIMARY solo accent — --indigo #5B5BF5
    coral: g.violet, // secondary solo accent — --violet #8B5CF6
    teal: g.teal, // --teal  #08314A — SURFACE-ONLY (1.49:1 vs bg); marks/text use semantic.positiveText
    tealMuted: g.teal2, // --teal-2 #041F35
    tealGlow: withAlpha(g.teal, 0.15), // selection glow (tracks --teal)
    // Hover for teal surfaces. No lighten()/darken() utility exists in the DS
    // (the only prior hover convention is Card's alpha-glow overlays), so the
    // documented formula is: HSL lightness +8 points, hue/sat preserved
    // (202.7°, 80.5%, 16.1% → 24.1%).
    tealHover: '#0C496F',
    slateBlue: g.indigo, // --indigo #5B5BF5
    plum: g.violet, // --violet #8B5CF6
    cream: g.indigoSoft, // .chip.indigo #818cf8 (subtle light accent)
    brand: g.teal, // HornMark gradient base (#08314A)
    brandSecondary: '#03121D', // HornMark gradient end (the old #14B8A6→#0E8C82 HSL step ΔL −9.8 applied to #08314A)
  },
  semantic: {
    // 2026-07-05: the single success/--pos token is split. Large fills
    // (buttons, badges, panel washes) take positiveSurface; any text, numeral,
    // stroke, dot or selected border that must read against the dark ramp
    // takes positiveText.
    positiveSurface: g.pos, // #08314A — 1.49:1 vs bg, fill-only
    // Same hue family as #08314A (H 202.7°, S 80.5%) at L 55%. Computed WCAG
    // contrast: 7.24:1 vs #05070A (bg), 6.95:1 vs #0A0E14 (panel) — AA ≥4.5:1.
    positiveText: '#30A3E9',
    warning: g.warn, // --warn #F59E0B
    danger: g.neg, // --neg  #F87171
    info: g.info, // --info #60A5FA
  },
  border: {
    subtle: g.hairline, // --hairline rgba(255,255,255,0.04)
    default: g.border, // --border        #1A2330
    strong: g.borderStrong, // --border-strong #232F42
  },
  overlay: {
    scrim: 'rgba(0,0,0,0.60)',
    glass: 'rgba(10,14,20,0.70)', // --panel @ 0.70 (glass over cool base)
  },
} as const;

/**
 * Legacy flat alias kept so any `oryxPalette.*` reference still resolves.
 * Now points at Genspark values; `gensparkPalette` is the canonical source.
 */
export const oryxPalette = {
  brandPrimary: g.teal,
  brandSecondary: '#03121D',
  accentIndigo: g.indigo,
  accentViolet: g.violet,
  accentTeal: g.teal,
  accentSoftblue: g.softblue,
  baseBg: g.bg,
  basePanel: g.panel,
  baseElev: g.elev,
  baseElev2: g.elev2,
  textPrimary: g.text,
  textSecondary: g.text2,
  textTertiary: g.text3,
  textQuaternary: g.text4,
} as const;

export type Colors = typeof colors;
export type OryxPalette = typeof oryxPalette;
export type GensparkPalette = typeof gensparkPalette;
export type Gradients = typeof gradients;
export type ChannelColors = typeof channelColors;
