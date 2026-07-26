import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Divider,
  GensparkIcon,
  HornMark,
  Text,
  useGx,
  useTheme,
} from '@oryx/design-system';
import type { MeResponse, WorkspacesListResponse } from '@oryx/shared-types';
import { apiClient } from '../../lib/api/client';
import { isApiError } from '../../lib/errors';
import { useAppDispatch, useAppSelector } from '../../store';
import { signout, switchWorkspace } from '../../store/thunks/auth';
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
 * The workspace pill is a real button (2026-07-12). Team/Workspace Rev 2
 * shipped multi-workspace membership, invites, and switching, so as of this
 * wave it's a real switcher: GET /workspaces lists every real workspace the
 * account belongs to, and picking one calls POST /auth/switch-workspace (see
 * workspaceMenu.ts for the pure item-list model). Account settings and Sign
 * out are always present below the switch items.
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
  const queryClient = useQueryClient();
  const refreshToken = useAppSelector((s) => s.auth.refreshToken);
  const [menuOpen, setMenuOpen] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [switchError, setSwitchError] = useState<string | null>(null);

  const counts = navCounts(me);
  // Small, real list — every workspace the account belongs to, not paginated.
  // Fetched whenever /me is (not just while the menu is open) so the switch
  // items are ready the first time the pill is pressed, no extra spinner.
  const workspacesQuery = useQuery<WorkspacesListResponse>({
    queryKey: ['workspaces'],
    queryFn: () => apiClient().get<WorkspacesListResponse>('/workspaces'),
    enabled: !!me,
    staleTime: 30 * 1000,
  });
  const menu = me ? workspaceMenu(me, workspacesQuery.data?.workspaces ?? []) : null;

  const onMenuAction = (id: 'account' | 'signout' | `switch:${string}`) => {
    if (id === 'account') {
      setMenuOpen(false);
      // The same explicit-screen resolution every sidebar Settings press uses.
      onNavigate(findNavItem('settings'));
      return;
    }
    if (id === 'signout') {
      setMenuOpen(false);
      void dispatch(signout());
      return;
    }
    // 'switch:<workspaceId>' — the refresh token lives in Redux only for the
    // tab that just completed a live signin/signup (web never cookies it,
    // only the access token; see store/thunks/auth.ts persistTokens). A
    // cookie-restored session — the common case after any page reload — has
    // none, so this is surfaced honestly rather than silently doing nothing.
    const workspaceId = id.slice('switch:'.length);
    if (!refreshToken) {
      setSwitchError('Switching needs a fresh sign-in in this browser tab — please sign out and sign back in, then try again.');
      return;
    }
    void (async () => {
      setSwitchError(null);
      setSwitchingId(workspaceId);
      try {
        await dispatch(switchWorkspace(workspaceId, refreshToken));
        setMenuOpen(false);
        await queryClient.invalidateQueries({ queryKey: ['me'] });
        await queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      } catch (e) {
        setSwitchError(isApiError(e) ? e.message : 'Could not switch workspaces.');
      } finally {
        setSwitchingId(null);
      }
    })();
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
            testID="workspace-pill"
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
                {switchError ? (
                  <Text variant="caption" color="danger">{switchError}</Text>
                ) : null}
              </View>
              <Divider />
              {menu.items.map((item) => {
                const isSwitch = item.id.startsWith('switch:');
                const pending = switchingId !== null;
                const icon = item.id === 'account' ? 'Cog' : isSwitch ? 'Layers' : 'ChevRight';
                return (
                  <Pressable
                    key={item.id}
                    style={[styles.menuItem, pending && { opacity: 0.5 }]}
                    onPress={() => onMenuAction(item.id)}
                    disabled={pending}
                    accessibilityRole="button"
                    accessibilityLabel={item.label}
                    testID={`workspace-menu-item-${item.id}`}
                  >
                    <GensparkIcon
                      name={icon}
                      size={12}
                      color={
                        item.id === 'signout'
                          ? t.colors.semantic.danger
                          : t.colors.text.tertiary
                      }
                    />
                    <View style={{ flex: 1 }}>
                      <Text
                        variant="navLabel"
                        color={item.id === 'signout' ? undefined : 'secondary'}
                        style={item.id === 'signout' ? { color: t.colors.semantic.danger } : undefined}
                        numberOfLines={1}
                      >
                        {item.label}
                      </Text>
                      {item.sub ? (
                        <Text variant="navGroup" color="tertiary">{item.sub}</Text>
                      ) : null}
                    </View>
                  </Pressable>
                );
              })}
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
