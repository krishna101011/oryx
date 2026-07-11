import React from 'react';
import { Pressable, View } from 'react-native';
import { GensparkIcon, Text, gx, useTheme } from '@oryx/design-system';
import type { MeResponse } from '@oryx/shared-types';
import { type WebNavItem, findNavItem, navCounts } from './webNav';

/**
 * Web-only topbar — 1:1 visual port of app.jsx <TopBar/> + styles.css .topbar /
 * .crumbs / .cmd / .ticker-strip / .ai-btn / .icon-btn.
 *
 * The ticker strip is intentionally EMPTY: data.jsx's TICKERS were fake numbers.
 * Real market data is Phase 9. Rather than render invented prices, the strip
 * shows a single muted "Markets · live data pending" marker.
 *
 * The bell and gear are shortcuts to the sidebar's SYSTEM items ('activity' /
 * 'settings') — they route through the same onNavigate the sidebar uses, so
 * they cannot drift to a different destination. The bell's unread dot reads
 * the same navCounts.activityUnread as the sidebar's Activity badge.
 *
 * The command bar is a real button (2026-07-12): pressing it — or ⌘K/Ctrl+K,
 * which WebShell listens for — opens the search overlay. Its placeholder is
 * scoped to what search actually covers today (sources + recent items).
 */
export const WebTopBar: React.FC<{
  crumbs: [string, string];
  me?: MeResponse;
  onNavigate: (item: WebNavItem) => void;
  onOpenSearch: () => void;
}> = ({ crumbs, me, onNavigate, onOpenSearch }) => {
  const t = useTheme();
  const activityUnread = navCounts(me).activityUnread;
  return (
    <View style={gx.topbar}>
      {/* breadcrumbs */}
      <View style={{ flexDirection: 'row', alignItems: 'center', columnGap: 6, minWidth: 200 }}>
        <Text variant="bodySm" color="tertiary">{crumbs[0]}</Text>
        <GensparkIcon name="ChevRight" size={10} color={t.colors.text.tertiary} />
        <Text variant="bodySm" color="primary">{crumbs[1]}</Text>
      </View>

      {/* command bar — a real button opening the search overlay */}
      <Pressable
        style={gx.cmd}
        onPress={onOpenSearch}
        accessibilityRole="button"
        accessibilityLabel="Search"
      >
        <GensparkIcon name="Search" size={12} color={t.colors.text.tertiary} />
        <Text variant="bodySm" color="tertiary" numberOfLines={1} style={{ flex: 1 }}>
          Search sources and recent items…
        </Text>
        <View style={gx.cmdKbd}>
          <Text variant="caption" color="tertiary">⌘K</Text>
        </View>
      </Pressable>

      {/* ticker strip — pending real market data (Phase 9), no fake numbers */}
      <View style={{ flex: 1, flexDirection: 'row', justifyContent: 'flex-end', overflow: 'hidden' }}>
        <Text variant="mono" color="tertiary" numberOfLines={1}>
          Markets · live data pending
        </Text>
      </View>

      {/* actions */}
      <View style={{ flexDirection: 'row', alignItems: 'center', columnGap: 4 }}>
        {/*
         * AI Analyst is a pending surface (webNav 'ai', pending: true — feature
         * not built yet). Deliberately NOT pressable, and dimmed to the same
         * opacity the sidebar gives pending items, with the dot's "live" glow
         * removed — it must read "coming later", not "active button".
         */}
        <View style={[gx.aiBtn, { opacity: 0.45 }]}>
          <View
            style={{
              width: 5,
              height: 5,
              borderRadius: 2.5,
              backgroundColor: t.colors.accent.coral,
            }}
          />
          <Text variant="navLabel" color="primary">AI Analyst</Text>
        </View>
        <Pressable
          style={gx.iconBtn}
          onPress={() => onNavigate(findNavItem('activity'))}
          accessibilityRole="button"
          accessibilityLabel="Activity"
        >
          <GensparkIcon name="Bell" size={14} color={t.colors.text.secondary} />
          {activityUnread > 0 ? (
            // .bell-dot from styles.css — 5px --neg dot at top 6 / right 7.
            <View
              style={{
                position: 'absolute',
                top: 6,
                right: 7,
                width: 5,
                height: 5,
                borderRadius: 2.5,
                backgroundColor: t.colors.semantic.danger,
              }}
            />
          ) : null}
        </Pressable>
        <Pressable
          style={gx.iconBtn}
          onPress={() => onNavigate(findNavItem('settings'))}
          accessibilityRole="button"
          accessibilityLabel="Settings"
        >
          <GensparkIcon name="Cog" size={14} color={t.colors.text.secondary} />
        </Pressable>
      </View>
    </View>
  );
};
