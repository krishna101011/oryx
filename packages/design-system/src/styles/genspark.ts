import { StyleSheet, type TextStyle, type ViewStyle } from 'react-native';
import type { Theme } from '../tokens';
import { withAlpha } from '../tokens/colors';
import { useTheme } from '../theme/ThemeProvider';

/**
 * GENSPARK COMPONENT STYLES — exact 1:1 port of the real class rules in
 * docs/design-reference/styles.css. Each entry carries the source selector and
 * ports its padding / radius / border / color / font-size values verbatim
 * (px → RN points, same number). Box-shadow → see tokens/shadows.ts.
 *
 * THEMING PHASE B RESTRUCTURE (2026-07-17). The old static `gx` StyleSheet
 * embedded dark palette values, so gx-consuming surfaces kept dark pockets
 * after a light switch (the documented Phase A deferral). It is now split:
 *
 *  - `gxGeometry` — the 13 color-free keys, one static StyleSheet shared by
 *    both modes (`transparent` counts as color-free: it is mode-invariant).
 *  - `makeGx(theme)` — per-theme factory for the color-bearing keys that have
 *    real runtime consumers. Every wash that was an inlined rgba literal is
 *    rebuilt via withAlpha against the ACTIVE theme's tokens, so light mode
 *    gets the light wash family automatically.
 *  - `useGx()` — the consumption idiom: `const gx = useGx();` inside a
 *    component; call sites keep the exact `gx.<key>` shape they had.
 *
 * RETIRED (Phase B decision): the 17 color-bearing keys with zero runtime
 * consumers — card/cardHead/kpi/kpiLabel/kpiVal (the Card/CardHeader/KPI
 * components are the real themed equivalents), chipViolet/chipVioletText,
 * meter (ConfidenceMeter owns that anatomy), navDot, pageHead,
 * tblHeadCell/tblCell, heatCell, calDay/calToday/calEvent/calEventText.
 * Their source selectors remain documented in docs/design-reference/styles.css;
 * a future consumer ports them INTO the factory, not back into a static sheet.
 *
 * Chip color variants port the exact border/background/text triad per source
 * (.chip.teal/.indigo/.neg/.warn), including the 0.3 / 0.06 alphas — now as
 * token washes. fontFamily is applied at call sites via typography tokens.
 */

/** The 13 color-free (mode-invariant) keys — static, shared by both themes. */
export const gxGeometry = StyleSheet.create({
  cardBody: { padding: 12 } as ViewStyle, // .card-body { padding:12px }
  kpiDelta: { marginTop: 4 } as TextStyle,
  meterFill: { position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 3 } as ViewStyle,
  // .btn.primary { border-color:transparent } (gradient applied via LinearGradient)
  btnPrimary: { borderColor: 'transparent' } as ViewStyle,
  // .btn.ghost { background:transparent }
  btnGhost: { backgroundColor: 'transparent' } as ViewStyle,
  // .nav { padding:6px 8px 12px }
  nav: { paddingTop: 6, paddingHorizontal: 8, paddingBottom: 12 } as ViewStyle,
  // .nav-group { margin-top:10px }
  navGroup: { marginTop: 10 } as ViewStyle,
  // .nav-label { padding:6px 10px 4px }  (color --text-4, mono 9 / 0.15em UPPER)
  navLabel: { paddingTop: 6, paddingHorizontal: 10, paddingBottom: 4 } as ViewStyle,
  // .nav-item { padding:5px 10px; r:5; gap:9; color:--text-2 }
  navItem: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 9,
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 5,
    position: 'relative',
  } as ViewStyle,
  // .nav-item.active::before { left:-8 (here inset 0 inside item); w:2; h:14; r:2; accent-grad }
  navActiveBar: {
    position: 'absolute',
    left: 0,
    top: '50%',
    marginTop: -7,
    width: 2,
    height: 14,
    borderRadius: 2,
  } as ViewStyle,
  // .icon-btn { 28x28; r:4 }
  iconBtn: { width: 28, height: 28, borderRadius: 4, alignItems: 'center', justifyContent: 'center' } as ViewStyle,
  // .section { padding:16px 18px }
  section: { paddingVertical: 16, paddingHorizontal: 18 } as ViewStyle,
  // grid gaps (.grid { gap:12 })
  grid: { gap: 12 } as ViewStyle,
});

function makeThemedGx(t: Theme) {
  const c = t.colors;
  return StyleSheet.create({
    // .chip { padding:1px 7px; r:3; border:1px --border; bg:--elev; color:--text-2 }
    chip: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 4,
      paddingVertical: 1,
      paddingHorizontal: 7,
      borderRadius: 3,
      borderWidth: 1,
      borderColor: c.border.default,
      backgroundColor: c.bg.elevated,
    } as ViewStyle,
    chipText: { color: c.text.secondary } as TextStyle,
    // .chip.teal { color:--teal; border:rgba(--teal,0.3); bg:rgba(--teal,0.06) }
    // (2026-07-05 teal retirement: washes track accent.teal — the surface-wash
    // family in BOTH modes; chip TEXT must stay legible on the active ramp, so
    // it reads semantic.positiveText through the ACTIVE theme.)
    chipTeal: {
      borderColor: withAlpha(c.accent.teal, 0.3),
      backgroundColor: withAlpha(c.accent.teal, 0.06),
    } as ViewStyle,
    chipTealText: { color: c.semantic.positiveText } as TextStyle,
    // .chip.indigo { color:#818cf8; border:rgba(91,91,245,0.3); bg:rgba(91,91,245,0.06) }
    chipIndigo: {
      borderColor: withAlpha(c.accent.slateBlue, 0.3), // slateBlue holds --indigo
      backgroundColor: withAlpha(c.accent.slateBlue, 0.06),
    } as ViewStyle,
    chipIndigoText: { color: c.accent.cream } as TextStyle, // cream holds the chip-indigo ink
    // .chip.neg
    chipNeg: {
      borderColor: withAlpha(c.semantic.danger, 0.3),
      backgroundColor: withAlpha(c.semantic.danger, 0.06),
    } as ViewStyle,
    chipNegText: { color: c.semantic.danger } as TextStyle,
    // .chip.warn
    chipWarn: {
      borderColor: withAlpha(c.semantic.warning, 0.3),
      backgroundColor: withAlpha(c.semantic.warning, 0.06),
    } as ViewStyle,
    chipWarnText: { color: c.semantic.warning } as TextStyle,

    // .btn { padding:5px 11px; r:5; bg:--elev; border:1px --border; font-size:11.5; color:--text }
    btn: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 6,
      paddingVertical: 5,
      paddingHorizontal: 11,
      borderRadius: 5,
      backgroundColor: c.bg.elevated,
      borderWidth: 1,
      borderColor: c.border.default,
    } as ViewStyle,
    btnText: { color: c.text.primary } as TextStyle,
    // .btn.primary color:#fff — text.inverse holds #fff in BOTH modes (mode-
    // invariant per styles.css:281 + the light-palette WCAG check: white on
    // indigo 4.93:1, white on light violet 6.09:1), resolved through the theme.
    btnPrimaryText: { color: c.text.inverse } as TextStyle,

    // ----- App shell (web) -----
    // .sidebar { width 232 (grid col); border-right:1px --border }
    sidebar: { width: 232, borderRightWidth: 1, borderRightColor: c.border.default } as ViewStyle,
    // .sidebar-brand { padding:14px; gap:10px; border-bottom:1px --border }
    sidebarBrand: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 10,
      padding: 14,
      borderBottomWidth: 1,
      borderBottomColor: c.border.default,
    } as ViewStyle,
    // .sidebar-brand .badge { font-size:9; color:--teal; border:1px rgba(--teal,0.3); pad:1px 5px; r:2 }
    brandBadge: {
      marginLeft: 'auto',
      borderWidth: 1,
      borderColor: withAlpha(c.accent.teal, 0.3),
      paddingVertical: 1,
      paddingHorizontal: 5,
      borderRadius: 2,
    } as ViewStyle,
    // .workspace-pill { margin:10px 10px 6px; pad:7px 9px; bg:--elev; border:1px --border; r:6 }
    workspacePill: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 8,
      marginHorizontal: 10,
      marginTop: 10,
      marginBottom: 6,
      paddingVertical: 7,
      paddingHorizontal: 9,
      backgroundColor: c.bg.elevated,
      borderWidth: 1,
      borderColor: c.border.default,
      borderRadius: 6,
    } as ViewStyle,
    // .ws-icon { 18x18; r:4 }
    wsIcon: {
      width: 18,
      height: 18,
      borderRadius: 4,
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: withAlpha(c.accent.teal, 0.12),
      borderWidth: 1,
      borderColor: withAlpha(c.accent.teal, 0.3),
    } as ViewStyle,
    // .nav-item.active { background:rgba(91,91,245,0.10) }
    navItemActive: { backgroundColor: withAlpha(c.accent.slateBlue, 0.1) } as ViewStyle,
    // .nav-badge { font-size:9; bg:--elev-2; color:--text-2; pad:1px 5px; r:8; border:1px --border }
    navBadge: {
      marginLeft: 'auto',
      backgroundColor: c.bg.elevated2,
      paddingVertical: 1,
      paddingHorizontal: 5,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: c.border.default,
    } as ViewStyle,
    navBadgeText: { color: c.text.secondary } as TextStyle,
    // .sidebar-foot { border-top:1px --border; padding:10px; gap:8 }
    sidebarFoot: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 8,
      borderTopWidth: 1,
      borderTopColor: c.border.default,
      padding: 10,
    } as ViewStyle,
    // .avatar { 26x26; r:50%; border:1px --border-strong }  (gradient via LinearGradient)
    avatar: {
      width: 26,
      height: 26,
      borderRadius: 13,
      borderWidth: 1,
      borderColor: c.border.strong,
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'hidden',
    } as ViewStyle,
    // Source: 6px --teal presence dot. A dot must READ against the active ramp
    // (the 2026-07-05 rule: dots use semantic.positiveText, never accent.teal —
    // post-retirement accent.teal is a 1.49:1 surface wash, invisible as a dot
    // in both modes). Flagged as a deliberate delta in the Phase B report.
    statusDot: {
      marginLeft: 'auto',
      width: 6,
      height: 6,
      borderRadius: 3,
      backgroundColor: c.semantic.positiveText,
    } as ViewStyle,

    // .topbar { height:44 (grid row); border-bottom:1px --border; bg:--bg; padding:0 12px; gap:12 }
    topbar: {
      height: 44,
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 12,
      borderBottomWidth: 1,
      borderBottomColor: c.border.default,
      backgroundColor: c.bg.primary,
      paddingHorizontal: 12,
    } as ViewStyle,
    // .cmd { bg:--elev; border:1px --border; r:5; padding:5px 9px }
    cmd: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 8,
      backgroundColor: c.bg.elevated,
      borderWidth: 1,
      borderColor: c.border.default,
      borderRadius: 5,
      paddingVertical: 5,
      paddingHorizontal: 9,
      flex: 1,
      maxWidth: 380,
    } as ViewStyle,
    cmdKbd: {
      marginLeft: 'auto',
      borderWidth: 1,
      borderColor: c.border.default,
      borderRadius: 3,
      paddingVertical: 1,
      paddingHorizontal: 5,
    } as ViewStyle,
    // .ai-btn { padding:5px 9px; bg:accent-grad-soft; border:1px rgba(139,92,246,0.3); r:5 }
    aiBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      columnGap: 6,
      paddingVertical: 5,
      paddingHorizontal: 9,
      borderWidth: 1,
      borderColor: withAlpha(c.accent.plum, 0.3), // plum holds --violet
      borderRadius: 5,
      backgroundColor: withAlpha(c.accent.plum, 0.1), // accent-grad-soft, solid approx
    } as ViewStyle,
  });
}

/** The merged sheet consumers receive: 13 geometry + 28 themed keys. */
export type Gx = typeof gxGeometry & ReturnType<typeof makeThemedGx>;

/**
 * Per-theme cache: exactly one StyleSheet.create per theme object (two exist),
 * so useGx() is referentially stable across renders and mode switches swap
 * between two stable sheets.
 */
const gxCache = new WeakMap<Theme, Gx>();

export function makeGx(theme: Theme): Gx {
  const cached = gxCache.get(theme);
  if (cached) return cached;
  const sheet: Gx = { ...gxGeometry, ...makeThemedGx(theme) };
  gxCache.set(theme, sheet);
  return sheet;
}

/** The gx consumption idiom: `const gx = useGx();` — tracks the active theme. */
export function useGx(): Gx {
  return makeGx(useTheme());
}
