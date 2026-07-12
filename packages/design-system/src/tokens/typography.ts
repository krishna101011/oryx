/**
 * Typography tokens — GENSPARK PORT (2026-06-29).
 *
 * Font choice (styles.css :root):
 *   --font-ui:   'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif
 *   --font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace
 *
 * Inter (400/500/600/700) and JetBrains Mono (400/500/600) are loaded at
 * startup via @expo-google-fonts (see apps/mobile/src/lib/fonts.ts). The
 * fontFamily strings below match the loaded names exactly.
 *
 * CSS letter-spacing is in `em`; RN letterSpacing is in points. Converted at
 * the rule's own font-size: points = em × fontSize (e.g. -0.01em @16px = -0.16).
 * Each variant cites the exact CSS rule it ports.
 *
 * NOTE: the historic "strict six-size" constraint is relaxed here because the
 * Genspark system genuinely uses more discrete sizes (9–22px). The variant set
 * mirrors the source's real type scale; Text.tsx's `variant` union is widened
 * to match. No call site invents an ad-hoc size — they pick a variant.
 */

const INTER_400 = 'Inter_400Regular';
const INTER_500 = 'Inter_500Medium';
const INTER_600 = 'Inter_600SemiBold';
const INTER_700 = 'Inter_700Bold';
const MONO_400 = 'JetBrainsMono_400Regular';
const MONO_500 = 'JetBrainsMono_500Medium';
const MONO_600 = 'JetBrainsMono_600SemiBold';

export const fontFamilies = {
  ui: { 400: INTER_400, 500: INTER_500, 600: INTER_600, 700: INTER_700 },
  mono: { 400: MONO_400, 500: MONO_500, 600: MONO_600 },
} as const;

export const typography = {
  // .page-head .title — font-size:16; font-weight:600; letter-spacing:-0.01em
  pageTitle: {
    fontFamily: INTER_600,
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 22, // 1.4 (no explicit lh; body line-height 1.45 → ~22)
    letterSpacing: -0.16, // -0.01em × 16
  },
  // .kpi .val — font-size:22; font-weight:600; letter-spacing:-0.02em; mono
  kpiVal: {
    fontFamily: MONO_600,
    fontSize: 22,
    fontWeight: '600' as const,
    lineHeight: 26,
    letterSpacing: -0.44, // -0.02em × 22
  },
  // .sidebar-brand .word — font-size:14; weight 600; letter-spacing:0.22em; ui
  wordmark: {
    fontFamily: INTER_600,
    fontSize: 14,
    fontWeight: '600' as const,
    lineHeight: 18,
    letterSpacing: 3.08, // 0.22em × 14
  },
  // .card-head .title — font-size:11.5; weight 600; letter-spacing:0.04em; UPPER
  cardTitle: {
    fontFamily: INTER_600,
    fontSize: 11.5,
    fontWeight: '600' as const,
    lineHeight: 16,
    letterSpacing: 0.46, // 0.04em × 11.5
    // text-transform: uppercase is part of the source rule (styles.css:316) —
    // carried in the token so call sites keep natural-case strings.
    textTransform: 'uppercase' as const,
  },
  // .nav-item — font-size:12; (weight 400/500); --font-ui
  navLabel: {
    fontFamily: INTER_500,
    fontSize: 12,
    fontWeight: '500' as const,
    lineHeight: 16,
    letterSpacing: 0,
  },
  // .nav-label (group) — font-size:9; letter-spacing:0.15em; mono UPPER
  navGroup: {
    fontFamily: MONO_500,
    fontSize: 9,
    fontWeight: '500' as const,
    lineHeight: 12,
    letterSpacing: 1.35, // 0.15em × 9
  },
  // body — html/body font-size:12.5; line-height:1.45; --font-ui (weight 400)
  body: {
    fontFamily: INTER_400,
    fontSize: 12.5,
    fontWeight: '400' as const,
    lineHeight: 18, // 1.45 × 12.5 ≈ 18.1
    letterSpacing: 0,
  },
  // table.tbl / .btn / .cmd — font-size:11.5; --font-ui (weight 400)
  bodySm: {
    fontFamily: INTER_400,
    fontSize: 11.5,
    fontWeight: '400' as const,
    lineHeight: 16,
    letterSpacing: 0,
  },
  // .chip — font-size:10; mono; letter-spacing:0.04em
  caption: {
    fontFamily: MONO_400,
    fontSize: 10,
    fontWeight: '400' as const,
    lineHeight: 14,
    letterSpacing: 0.4, // 0.04em × 10
  },
  // .kpi .label / table th — font-size:9.5; mono; letter-spacing:0.1–0.12em UPPER
  label: {
    fontFamily: MONO_500,
    fontSize: 9.5,
    fontWeight: '500' as const,
    lineHeight: 12,
    letterSpacing: 0.95, // ~0.1em × 9.5
  },
  // .mono / .num — tabular numerics; letter-spacing:-0.01em; weight 500
  mono: {
    fontFamily: MONO_500,
    fontSize: 11.5,
    fontWeight: '500' as const,
    lineHeight: 16,
    letterSpacing: -0.115, // -0.01em × 11.5
  },
  // ---- retained alias variants (existing call sites) ----
  // display — largest UI title (no direct Genspark rule; kpiVal is the biggest
  // number). Mapped to weight-700 Inter at 32 for the few display call sites.
  display: {
    fontFamily: INTER_700,
    fontSize: 32,
    fontWeight: '700' as const,
    lineHeight: 38,
    letterSpacing: -0.32,
  },
  // h1 / h2 retained for screens that request them; weights match Genspark UI.
  h1: {
    fontFamily: INTER_700,
    fontSize: 24,
    fontWeight: '700' as const,
    lineHeight: 30,
    letterSpacing: -0.24,
  },
  h2: {
    fontFamily: INTER_600,
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 26,
    letterSpacing: -0.2,
  },
} as const;

export type Typography = typeof typography;
export type TextVariant = keyof Typography;
