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
    // 2026-07-16 theming Phase A: 0.60 → 0.55, consolidating the app's three
    // scrim literals (0.5 sheets, 0.55 backdrops, 0.60 token — the token had
    // zero consumers) onto the established WebSearchOverlay convention.
    scrim: 'rgba(0,0,0,0.55)',
    glass: 'rgba(10,14,20,0.70)', // --panel @ 0.70 (glass over cool base)
  },
} as const;

/**
 * ===========================================================================
 * LIGHT MODE (theming Phase A, 2026-07-16).
 * The core values (bg/panel/elev, text.primary, indigo, violet, the semantic
 * set, positiveSurface) are OWNER-PROVIDED and WCAG-verified — do not alter.
 * The remaining values are derived to occupy the same perceptual role as
 * their dark analog, each confirmed with a real WCAG ratio check
 * (scripted, relative-luminance):
 *   border   #D7DDE5  1.29:1 vs bg / 1.37:1 vs panel (dark analog #1A2330 is
 *                     1.27:1 / 1.22:1 — same subtle-hairline role)
 *   borderStrong #C4CDD9 1.51:1 vs bg (dark #232F42 is 1.50:1 — exact role)
 *   text2    #3E4756  8.82:1 vs bg (dark #A8B0BF is 9.25:1) — AAA
 *   text3    #556072  5.98:1 vs bg (dark #6B7588 is 4.35:1) — AA
 *   text4    #8A94A6  2.88:1 vs bg (dark #4A5263 is 2.57:1) — decorative ramp
 *                     step only, same as dark; never used for readable copy
 * Given values verified: text.primary 16.90:1, positiveText 6.64:1, danger
 * 7.25:1, warning 4.79:1, info 7.86:1, violet 5.73:1 (all vs bg #F7F8FA);
 * positiveText on positiveSurface 6.05:1; white on indigo 4.93:1, white on
 * light violet #7440D6 6.09:1 (Button primary label stays white).
 * ===========================================================================
 */
export const lightPalette = {
  bg: '#F7F8FA', // provided
  panel: '#FFFFFF', // provided
  elev: '#EDEFF3', // provided
  elev2: '#E2E6EC', // derived: one ramp step past elev (mirrors --elev-2)
  border: '#D7DDE5', // derived + contrast-checked (see block comment)
  borderStrong: '#C4CDD9', // derived: 1.51:1 vs bg == dark strong's 1.50:1
  hairline: 'rgba(20,23,28,0.05)', // text.primary channels @5% (mirrors 4%-white)

  text: '#14171C', // provided
  text2: '#3E4756', // derived, 8.82:1 vs bg
  text3: '#556072', // derived, 5.98:1 vs bg
  text4: '#8A94A6', // derived, decorative ramp step (2.88:1, matches dark role)

  indigo: '#5B5BF5', // provided — unchanged across modes
  violet: '#7440D6', // provided — light-verified violet (dark holds #8B5CF6)
  teal: '#E3EFFA', // provided positiveSurface — the light surface-wash family
  teal2: '#D2E4F6', // derived: same ΔL step the dark teal→teal-2 pair uses
  softblue: '#17517E', // == info (softblue tracks --info in both modes)
  pos: '#E3EFFA', // provided positiveSurface (fills only, like dark --pos)
  neg: '#9E241E', // provided danger
  warn: '#96640A', // provided warning
  info: '#17517E', // provided info

  indigoSoft: '#4338CA', // chip-indigo text, 7.44:1 vs bg (dark #818cf8 role)
  calEventText: '#4338CA', // calendar event text — same readable indigo family
  onAccent: '#FFFFFF', // white on accent fills verified above
} as const;

const l = lightPalette;

/** Light-mode gradients — same start/end roles as `gradients`, light values. */
export const lightGradients = {
  accent: { from: '#5B5BF5', to: '#7440D6', angle: 135 },
  accentSoft: { from: 'rgba(91,91,245,0.18)', to: 'rgba(116,64,214,0.18)', angle: 135 },
  // one shade off bg → bg, same 180° recede the dark sidebar uses
  sidebar: { from: '#FBFCFD', to: '#F7F8FA', angle: 180 },
  // muted-wash → full-wash, mirroring the dark teal-2→teal subtlety
  meterTeal: { from: '#D2E4F6', to: '#E3EFFA', angle: 90 },
  // muted-danger → danger (dark mirrors #b45a5a → --neg)
  meterNeg: { from: '#C0706B', to: '#9E241E', angle: 90 },
  // border-strong → elev, the dark avatar's exact role
  avatar: { from: '#C4CDD9', to: '#EDEFF3', angle: 135 },
} as const;

/**
 * Light structured colors — the SAME key shape as `colors`, light values.
 * HornMark note: accent.brand/brandSecondary keep the deep-navy gradient in
 * light mode (12.76:1 / 17.83:1 vs light bg — the mark reads strongly); the
 * cutout stroke follows bg.primary, which is what actually flips per mode.
 */
export const lightColors: { [K in keyof Colors]: { [J in keyof Colors[K]]: string } } = {
  bg: {
    primary: l.bg,
    secondary: l.elev, // recede gutter reads a shade off the app bg (role match)
    card: l.panel,
    elevated: l.elev,
    elevated2: l.elev2,
  },
  text: {
    primary: l.text,
    secondary: l.text2,
    tertiary: l.text3,
    inverse: '#FFFFFF', // white on saturated pill/accent fills (mode-invariant fills)
    onAmber: '#FFFFFF',
    onCoral: '#FFFFFF',
    // light teal is a pale wash — readable ink on it is positiveText (6.05:1)
    onTeal: '#155A9C',
  },
  accent: {
    amber: l.indigo,
    coral: l.violet,
    teal: l.teal, // surface wash, fill-only (same rule as dark)
    tealMuted: l.teal2,
    tealGlow: withAlpha(l.teal2, 0.6), // selection glow: deeper wash, light-legible
    tealHover: '#C0DAF3', // hover darkens on light (dark mode lightens): −8 L
    slateBlue: l.indigo,
    plum: l.violet,
    cream: l.indigoSoft,
    brand: '#08314A', // HornMark gradient base — kept (12.76:1 vs light bg)
    brandSecondary: '#03121D', // HornMark gradient end — kept (17.83:1)
  },
  semantic: {
    positiveSurface: '#E3EFFA', // provided
    positiveText: '#155A9C', // provided — 6.64:1 vs bg, 7.06:1 vs panel
    warning: l.warn,
    danger: l.neg,
    info: l.info,
  },
  border: {
    subtle: l.hairline,
    default: l.border,
    strong: l.borderStrong,
  },
  overlay: {
    scrim: 'rgba(0,0,0,0.55)', // scrims stay black-based in both modes
    glass: 'rgba(255,255,255,0.70)', // light panel @ 0.70
  },
};

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
export type LightPalette = typeof lightPalette;
export type OryxPalette = typeof oryxPalette;
export type GensparkPalette = typeof gensparkPalette;
export type Gradients = typeof gradients;
export type ChannelColors = typeof channelColors;
