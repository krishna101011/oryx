import React from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  GensparkIcon,
  HornMark,
  Text,
  gradients,
  gx,
  useTheme,
} from '@oryx/design-system';
import type { MeResponse } from '@oryx/shared-types';
import { WEB_NAV, type WebNavItem } from './webNav';

/**
 * Web-only left sidebar — 1:1 visual port of app.jsx <Sidebar/> + styles.css
 * .sidebar / .nav-item.active (left accent bar) / .workspace-pill / .sidebar-foot.
 *
 * Real data only: workspace name/role, profile display name + initials, and the
 * build version badge come from /me. No "Jordan Mehta" / "ORYX Editorial" / fake
 * counts — pending nav items render dimmed; badges show real /me counts only.
 */
function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '—';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

export const WebSidebar: React.FC<{
  me?: MeResponse;
  activeId: string;
  onNavigate: (item: WebNavItem) => void;
}> = ({ me, activeId, onNavigate }) => {
  const t = useTheme();

  const counts = {
    verifyPending: me?.verification.pendingReviewCount ?? 0,
    contentDrafts: me?.content.draftCount ?? 0,
    activityUnread: me?.activity.unreadCount ?? 0,
  };

  const wsName = me?.workspace.name ?? 'Workspace';
  const wsRole = me ? `${me.workspace.role.toUpperCase()} · ${me.workspace.kind.toUpperCase()}` : '';
  const displayName = me?.profile.displayName ?? '';
  const version = me?.build.version ? `v${me.build.version}` : '';

  return (
    <View style={[gx.sidebar, { height: '100%' }]}>
      <LinearGradient
        colors={[gradients.sidebar.from, gradients.sidebar.to]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0, y: 1 }}
        style={{ flex: 1 }}
      >
        {/* brand */}
        <View style={gx.sidebarBrand}>
          <HornMark size={22} />
          <Text variant="wordmark" color="primary">ORYX</Text>
          {version ? (
            <View style={gx.brandBadge}>
              <Text variant="navGroup" style={{ color: t.colors.accent.teal }}>{version}</Text>
            </View>
          ) : null}
        </View>

        {/* workspace pill (real) */}
        <View style={gx.workspacePill}>
          <View style={gx.wsIcon}>
            <HornMark size={12} />
          </View>
          <View style={{ flex: 1 }}>
            <Text variant="navLabel" color="primary" numberOfLines={1}>{wsName}</Text>
            {wsRole ? <Text variant="navGroup" color="tertiary">{wsRole}</Text> : null}
          </View>
          <GensparkIcon name="ChevDown" size={12} color={t.colors.text.tertiary} />
        </View>

        {/* nav */}
        <ScrollView style={{ flex: 1 }} contentContainerStyle={gx.nav}>
          {WEB_NAV.map((g) => (
            <View key={g.group} style={gx.navGroup}>
              <View style={gx.navLabel}>
                <Text variant="navGroup" color="tertiary">{g.group}</Text>
              </View>
              {g.items.map((it) => {
                const active = it.id === activeId;
                const badge = it.countKey ? counts[it.countKey] : 0;
                const iconColor = active ? t.colors.accent.coral : t.colors.text.tertiary;
                return (
                  <Pressable
                    key={it.id}
                    onPress={() => onNavigate(it)}
                    disabled={it.pending}
                    style={[gx.navItem, active && gx.navItemActive, it.pending && { opacity: 0.45 }]}
                  >
                    {active ? (
                      <LinearGradient
                        colors={[gradients.accent.from, gradients.accent.to]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={gx.navActiveBar}
                      />
                    ) : null}
                    <GensparkIcon name={it.icon} size={14} color={iconColor} />
                    <Text variant="navLabel" color={active ? 'primary' : 'secondary'} numberOfLines={1}>
                      {it.label}
                    </Text>
                    {badge > 0 ? (
                      <View style={gx.navBadge}>
                        <Text variant="navGroup" style={gx.navBadgeText}>{String(badge)}</Text>
                      </View>
                    ) : null}
                  </Pressable>
                );
              })}
            </View>
          ))}
        </ScrollView>

        {/* foot (real profile) */}
        {displayName ? (
          <View style={gx.sidebarFoot}>
            <LinearGradient
              colors={[gradients.avatar.from, gradients.avatar.to]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={gx.avatar}
            >
              <Text variant="label" color="primary">{initialsOf(displayName)}</Text>
            </LinearGradient>
            <View style={{ flex: 1 }}>
              <Text variant="navLabel" color="primary" numberOfLines={1}>{displayName}</Text>
              {me ? <Text variant="navGroup" color="tertiary">{me.workspace.role.toUpperCase()}</Text> : null}
            </View>
            <View style={gx.statusDot} />
          </View>
        ) : null}
      </LinearGradient>
    </View>
  );
};
