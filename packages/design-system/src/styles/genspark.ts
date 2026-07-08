import { StyleSheet, type TextStyle, type ViewStyle } from 'react-native';
import { colors, gensparkPalette as g, tealAlpha } from '../tokens/colors';

/**
 * GENSPARK COMPONENT STYLES — exact 1:1 port of the real class rules in
 * docs/design-reference/styles.css. Each StyleSheet entry carries the source
 * selector and ports its padding / radius / border / color / font-size values
 * verbatim (px → RN points, same number). Box-shadow → see tokens/shadows.ts.
 *
 * Chip color variants port the exact border/background/text triad per source
 * (.chip.teal/.violet/.indigo/.neg/.warn), including the 0.3 / 0.06 alphas.
 *
 * Consumed by the web sidebar shell and available to any screen. fontFamily is
 * applied at call sites via the typography tokens; sizes here match the CSS.
 */
export const gx = StyleSheet.create({
  // .card  { background:--panel; border:1px --border; border-radius:6px }
  card: {
    backgroundColor: g.panel,
    borderWidth: 1,
    borderColor: g.border,
    borderRadius: 6,
  } as ViewStyle,
  // .card-head { padding:9px 12px; border-bottom:1px --border }
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: g.border,
    columnGap: 8,
  } as ViewStyle,
  cardBody: { padding: 12 } as ViewStyle, // .card-body { padding:12px }

  // .kpi { padding:12px 14px; background:--panel; border:1px --border; r:6 }
  kpi: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    backgroundColor: g.panel,
    borderWidth: 1,
    borderColor: g.border,
    borderRadius: 6,
  } as ViewStyle,
  kpiLabel: { color: g.text4 } as TextStyle, // mono 9.5 / 0.12em UPPER
  kpiVal: { color: g.text, marginTop: 6 } as TextStyle, // 22 / 600 / -0.02em
  kpiDelta: { marginTop: 4 } as TextStyle,

  // .chip { padding:1px 7px; r:3; border:1px --border; bg:--elev; color:--text-2 }
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 4,
    paddingVertical: 1,
    paddingHorizontal: 7,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: g.border,
    backgroundColor: g.elev,
  } as ViewStyle,
  chipText: { color: g.text2 } as TextStyle,
  // .chip.teal { color:--teal; border:rgba(--teal,0.3); bg:rgba(--teal,0.06) }
  // (2026-07-05 teal retirement: washes track tealAlpha; chip TEXT must stay
  // legible on the dark ramp, so it reads semantic.positiveText, not --teal.)
  chipTeal: { borderColor: tealAlpha(0.3), backgroundColor: tealAlpha(0.06) } as ViewStyle,
  chipTealText: { color: colors.semantic.positiveText } as TextStyle,
  // .chip.violet
  chipViolet: { borderColor: 'rgba(139,92,246,0.3)', backgroundColor: 'rgba(139,92,246,0.06)' } as ViewStyle,
  chipVioletText: { color: g.violet } as TextStyle,
  // .chip.indigo { color:#818cf8; border:rgba(91,91,245,0.3); bg:rgba(91,91,245,0.06) }
  chipIndigo: { borderColor: 'rgba(91,91,245,0.3)', backgroundColor: 'rgba(91,91,245,0.06)' } as ViewStyle,
  chipIndigoText: { color: g.indigoSoft } as TextStyle,
  // .chip.neg
  chipNeg: { borderColor: 'rgba(248,113,113,0.3)', backgroundColor: 'rgba(248,113,113,0.06)' } as ViewStyle,
  chipNegText: { color: g.neg } as TextStyle,
  // .chip.warn
  chipWarn: { borderColor: 'rgba(245,158,11,0.3)', backgroundColor: 'rgba(245,158,11,0.06)' } as ViewStyle,
  chipWarnText: { color: g.warn } as TextStyle,

  // .meter { height:6px; background:--elev; border-radius:3px; overflow:hidden }
  meter: { height: 6, backgroundColor: g.elev, borderRadius: 3, overflow: 'hidden' } as ViewStyle,
  meterFill: { position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 3 } as ViewStyle,

  // .btn { padding:5px 11px; r:5; bg:--elev; border:1px --border; font-size:11.5; color:--text }
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 6,
    paddingVertical: 5,
    paddingHorizontal: 11,
    borderRadius: 5,
    backgroundColor: g.elev,
    borderWidth: 1,
    borderColor: g.border,
  } as ViewStyle,
  btnText: { color: g.text } as TextStyle,
  // .btn.primary { background:--accent-grad; border-color:transparent; color:#fff; weight 500 }
  btnPrimary: { borderColor: 'transparent' } as ViewStyle, // gradient applied via LinearGradient
  btnPrimaryText: { color: g.onAccent } as TextStyle,
  // .btn.ghost { background:transparent }
  btnGhost: { backgroundColor: 'transparent' } as ViewStyle,

  // ----- App shell (web) -----
  // .sidebar { width 232 (grid col); border-right:1px --border }
  sidebar: { width: 232, borderRightWidth: 1, borderRightColor: g.border } as ViewStyle,
  // .sidebar-brand { padding:14px; gap:10px; border-bottom:1px --border }
  sidebarBrand: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 10,
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: g.border,
  } as ViewStyle,
  // .sidebar-brand .badge { font-size:9; color:--teal; border:1px rgba(--teal,0.3); pad:1px 5px; r:2 }
  brandBadge: {
    marginLeft: 'auto',
    borderWidth: 1,
    borderColor: tealAlpha(0.3),
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
    backgroundColor: g.elev,
    borderWidth: 1,
    borderColor: g.border,
    borderRadius: 6,
  } as ViewStyle,
  // .ws-icon { 18x18; r:4 }
  wsIcon: {
    width: 18,
    height: 18,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tealAlpha(0.12),
    borderWidth: 1,
    borderColor: tealAlpha(0.3),
  } as ViewStyle,
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
  // .nav-item.active { background:rgba(91,91,245,0.10) }
  navItemActive: { backgroundColor: 'rgba(91,91,245,0.10)' } as ViewStyle,
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
  // .nav-badge { font-size:9; bg:--elev-2; color:--text-2; pad:1px 5px; r:8; border:1px --border }
  navBadge: {
    marginLeft: 'auto',
    backgroundColor: g.elev2,
    paddingVertical: 1,
    paddingHorizontal: 5,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: g.border,
  } as ViewStyle,
  navBadgeText: { color: g.text2 } as TextStyle,
  // .nav-dot { 5x5; r:50%; bg:--teal; glow }
  navDot: { marginLeft: 'auto', width: 5, height: 5, borderRadius: 2.5, backgroundColor: g.teal } as ViewStyle,
  // .sidebar-foot { border-top:1px --border; padding:10px; gap:8 }
  sidebarFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    borderTopWidth: 1,
    borderTopColor: g.border,
    padding: 10,
  } as ViewStyle,
  // .avatar { 26x26; r:50%; border:1px --border-strong }  (gradient via LinearGradient)
  avatar: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: g.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  } as ViewStyle,
  statusDot: { marginLeft: 'auto', width: 6, height: 6, borderRadius: 3, backgroundColor: g.teal } as ViewStyle,

  // .topbar { height:44 (grid row); border-bottom:1px --border; bg:--bg; padding:0 12px; gap:12 }
  topbar: {
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 12,
    borderBottomWidth: 1,
    borderBottomColor: g.border,
    backgroundColor: g.bg,
    paddingHorizontal: 12,
  } as ViewStyle,
  // .cmd { bg:--elev; border:1px --border; r:5; padding:5px 9px }
  cmd: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    backgroundColor: g.elev,
    borderWidth: 1,
    borderColor: g.border,
    borderRadius: 5,
    paddingVertical: 5,
    paddingHorizontal: 9,
    flex: 1,
    maxWidth: 380,
  } as ViewStyle,
  cmdKbd: {
    marginLeft: 'auto',
    borderWidth: 1,
    borderColor: g.border,
    borderRadius: 3,
    paddingVertical: 1,
    paddingHorizontal: 5,
  } as ViewStyle,
  // .icon-btn { 28x28; r:4 }
  iconBtn: { width: 28, height: 28, borderRadius: 4, alignItems: 'center', justifyContent: 'center' } as ViewStyle,
  // .ai-btn { padding:5px 9px; bg:accent-grad-soft; border:1px rgba(139,92,246,0.3); r:5 }
  aiBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 6,
    paddingVertical: 5,
    paddingHorizontal: 9,
    borderWidth: 1,
    borderColor: 'rgba(139,92,246,0.3)',
    borderRadius: 5,
    backgroundColor: 'rgba(139,92,246,0.10)', // accent-grad-soft, solid approx
  } as ViewStyle,

  // .page-head { padding:14px 18px 12px; border-bottom:1px --border; bg:--bg; gap:12 }
  pageHead: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 12,
    paddingTop: 14,
    paddingHorizontal: 18,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: g.border,
    backgroundColor: g.bg,
  } as ViewStyle,
  // .section { padding:16px 18px }
  section: { paddingVertical: 16, paddingHorizontal: 18 } as ViewStyle,

  // table.tbl th { padding:6px 10px; border-bottom:1px --border } td { padding:5px 10px; border-bottom hairline }
  tblHeadCell: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderBottomWidth: 1,
    borderBottomColor: g.border,
  } as ViewStyle,
  tblCell: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderBottomWidth: 1,
    borderBottomColor: g.hairline,
  } as ViewStyle,

  // .heat-cell { border:1px rgba(255,255,255,0.03); r:3; padding:6px 8px }
  heatCell: {
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.03)',
    borderRadius: 3,
    paddingVertical: 6,
    paddingHorizontal: 8,
    justifyContent: 'space-between',
  } as ViewStyle,

  // .cal .day { bg:--panel; border:1px --border; padding:6px 8px }
  calDay: {
    backgroundColor: g.panel,
    borderWidth: 1,
    borderColor: g.border,
    paddingVertical: 6,
    paddingHorizontal: 8,
    aspectRatio: 1.4,
  } as ViewStyle,
  // .cal .day.today { border-color:--violet }
  calToday: { borderColor: g.violet } as ViewStyle,
  // .cal .event { r:2; padding:1px 4px; bg:rgba(91,91,245,0.15); color:#b5b7ff }
  calEvent: {
    position: 'absolute',
    left: 4,
    right: 4,
    bottom: 4,
    borderRadius: 2,
    paddingVertical: 1,
    paddingHorizontal: 4,
    backgroundColor: 'rgba(91,91,245,0.15)',
  } as ViewStyle,
  calEventText: { color: g.calEventText } as TextStyle,

  // grid gaps (.grid { gap:12 })
  grid: { gap: 12 } as ViewStyle,
});
