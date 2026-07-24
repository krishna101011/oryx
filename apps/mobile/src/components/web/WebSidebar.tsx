import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  Divider,
  GensparkIcon,
  HornMark,
  Text,
  useGx,
  useTheme,
} from '@oryx/design-system';
import type { MeResponse } from '@oryx/shared-types';
import { useAppDispatch } from '../../store';
import { signout } from '../../store/thunks/auth';
import { WEB_NAV, type WebNavItem, findNavItem, navCounts } from './webNav';
import { workspaceMenu } from './workspaceMenu';

/**
 * Web-only left sidebar — 1:1 visual port of app.jsx <Sidebar/> + styles.css
 * .sidebar / .nav-item.active (left accent bar) / .workspace-pill / .sidebar-foot.
 *
 * Real data only: workspace name/role, profile display name + initials, and the
 * build version badge come from /me. No "Jordan Mehta" / "ORYX Editorial" / fake
 * counts — pending nav items render dimmed; badges show real /me counts only.
 *
 * The workspace pill is a real button (2026-07-12): it opens an honestly-scoped
 * menu — current workspace facts, Account settings, Sign out. Deliberately NOT
 * a workspace switcher: exactly one workspace exists per account today
 * (Team/Workspace architecture is frozen but unbuilt), so there is nothing to
 * switch to — see workspaceMenu.ts.
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
  const gx = useGx();
  const dispatch = useAppDispatch();
  const [menuOpen, setMenuOpen] = useState(false);

  const counts = navCounts(me);
  const menu = me ? workspaceMenu(me) : null;

  const onMenuAction = (id: 'account' | 'signout') => {
    setMenuOpen(false);
    if (id === 'account') {
      // The same explicit-screen resolution every sidebar Settings press uses.
      onNavigate(findNavItem('settings'));
    } else {
      void dispatch(signout());
    }
  };

  const wsName = me?.workspace.name ?? 'Workspace';
  const wsRole = me ? `${me.workspace.role.toUpperCase()} · ${me.workspace.kind.toUpperCase()}` : '';
  const displayName = me?.profile.displayName ?? '';
  const version = me?.build.version ? `v${me.build.version}` : '';

  return (
    <View style={[gx.sidebar, { height: '100%' }]}>
      <LinearGradient
        colors={[t.gradients.sidebar.from, t.gradients.sidebar.to]}
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
              <Text variant="navGroup" style={{ color: t.colors.semantic.positiveText }}>{version}</Text>
            </View>
          ) : null}
        </View>

        {/* workspace pill (real) — opens the workspace menu */}
        <View style={styles.pillWrap}>
          <Pressable
            style={gx.workspacePill}
            onPress={() => setMenuOpen((v) => !v)}
            disabled={!menu}
            accessibilityRole="button"
            accessibilityLabel="Workspace menu"
          >
            <View style={gx.wsIcon}>
              <HornMark size={12} />
            </View>
            <View style={{ flex: 1 }}>
              <Text variant="navLabel" color="primary" numberOfLines={1}>{wsName}</Text>
              {wsRole ? <Text variant="navGroup" color="tertiary">{wsRole}</Text> : null}
            </View>
            <GensparkIcon
              name={menuOpen ? 'ChevUp' : 'ChevDown'}
              size={12}
              color={t.colors.text.tertiary}
            />
          </Pressable>
          {menuOpen && menu ? (
            <View
              style={[
                styles.menu,
                { backgroundColor: t.colors.bg.card, borderColor: t.colors.border.strong },
              ]}
            >
              <View style={styles.menuHeader}>
                <Text variant="navLabel" color="primary" numberOfLines={1}>{menu.name}</Text>
                <Text variant="navGroup" color="tertiary">{menu.meta}</Text>
                <Text variant="caption" color="tertiary">{menu.note}</Text>
              </View>
              <Divider />
              {menu.items.map((item) => (
                <Pressable
                  key={item.id}
                  style={styles.menuItem}
                  onPress={() => onMenuAction(item.id)}
                  accessibilityRole="button"
                  accessibilityLabel={item.label}
                >
                  <GensparkIcon
                    name={item.id === 'account' ? 'Cog' : 'ChevRight'}
                    size={12}
                    color={
                      item.id === 'signout'
                        ? t.colors.semantic.danger
                        : t.colors.text.tertiary
                    }
                  />
                  <Text
                    variant="navLabel"
                    color={item.id === 'signout' ? undefined : 'secondary'}
                    style={item.id === 'signout' ? { color: t.colors.semantic.danger } : undefined}
                  >
                    {item.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : null}
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
                        colors={[t.gradients.accent.from, t.gradients.accent.to]}
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
              colors={[t.gradients.avatar.from, t.gradients.avatar.to]}
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

const styles = StyleSheet.create({
  // zIndex keeps the dropdown above the nav ScrollView that follows it.
  pillWrap: { zIndex: 20 },
  menu: {
    position: 'absolute',
    top: '100%',
    left: 10,
    right: 10,
    borderWidth: 1,
    borderRadius: 6,
    paddingVertical: 4,
    zIndex: 21,
  },
  menuHeader: { paddingHorizontal: 10, paddingVertical: 8, rowGap: 2 },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
});
