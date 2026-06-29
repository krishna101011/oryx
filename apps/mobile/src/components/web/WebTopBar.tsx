import React from 'react';
import { View } from 'react-native';
import { GensparkIcon, Text, gx, useTheme } from '@oryx/design-system';

/**
 * Web-only topbar — 1:1 visual port of app.jsx <TopBar/> + styles.css .topbar /
 * .crumbs / .cmd / .ticker-strip / .ai-btn / .icon-btn.
 *
 * The ticker strip is intentionally EMPTY: data.jsx's TICKERS were fake numbers.
 * Real market data is Phase 9. Rather than render invented prices, the strip
 * shows a single muted "Markets · live data pending" marker.
 */
export const WebTopBar: React.FC<{ crumbs: [string, string] }> = ({ crumbs }) => {
  const t = useTheme();
  return (
    <View style={gx.topbar}>
      {/* breadcrumbs */}
      <View style={{ flexDirection: 'row', alignItems: 'center', columnGap: 6, minWidth: 200 }}>
        <Text variant="bodySm" color="tertiary">{crumbs[0]}</Text>
        <GensparkIcon name="ChevRight" size={10} color={t.colors.text.tertiary} />
        <Text variant="bodySm" color="primary">{crumbs[1]}</Text>
      </View>

      {/* command bar */}
      <View style={gx.cmd}>
        <GensparkIcon name="Search" size={12} color={t.colors.text.tertiary} />
        <Text variant="bodySm" color="tertiary" numberOfLines={1} style={{ flex: 1 }}>
          Search markets, claims, sources, drafts…
        </Text>
        <View style={gx.cmdKbd}>
          <Text variant="caption" color="tertiary">⌘K</Text>
        </View>
      </View>

      {/* ticker strip — pending real market data (Phase 9), no fake numbers */}
      <View style={{ flex: 1, flexDirection: 'row', justifyContent: 'flex-end', overflow: 'hidden' }}>
        <Text variant="mono" color="tertiary" numberOfLines={1}>
          Markets · live data pending
        </Text>
      </View>

      {/* actions */}
      <View style={{ flexDirection: 'row', alignItems: 'center', columnGap: 4 }}>
        <View style={gx.aiBtn}>
          <View
            style={{
              width: 5,
              height: 5,
              borderRadius: 2.5,
              backgroundColor: t.colors.accent.coral,
              shadowColor: t.colors.accent.coral,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: 0.6,
              shadowRadius: 3,
            }}
          />
          <Text variant="navLabel" color="primary">AI Analyst</Text>
        </View>
        <View style={gx.iconBtn}>
          <GensparkIcon name="Bell" size={14} color={t.colors.text.secondary} />
        </View>
        <View style={gx.iconBtn}>
          <GensparkIcon name="Cog" size={14} color={t.colors.text.secondary} />
        </View>
      </View>
    </View>
  );
};
