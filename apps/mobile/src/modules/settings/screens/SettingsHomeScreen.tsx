import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Screen,
  Spacer,
  Text,
} from '@oryx/design-system';
import type {
  MeResponse,
  Preferences,
  ThemeMode,
  UpdatePreferencesRequest,
} from '@oryx/shared-types';
import { useMe } from '../../../hooks/useMe';
import { apiClient } from '../../../lib/api/client';
import { useAppDispatch, useAppSelector } from '../../../store';
import { themeActions } from '../../../store/slices/theme';
import { signout } from '../../../store/thunks/auth';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { SettingsRow } from '../components/SettingsRow';

const THEME_COPY: Record<ThemeMode, { label: string; description: string }> = {
  dark: { label: 'Dark', description: 'The ORYX terminal baseline' },
  light: { label: 'Light', description: 'High-glare and print-adjacent work' },
};
const THEME_MODES: ThemeMode[] = ['dark', 'light'];

export const SettingsHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const queryClient = useQueryClient();
  const me = useMe();
  const mode = useAppSelector((s) => s.theme.mode);

  // Theming Phase A: the switch applies instantly via Redux (onMutate) and
  // persists account-synced through the real Preferences PATCH. On success the
  // ['me'] cache is patched in place so useMe's hydration effect agrees with
  // the local state instead of flickering back on the next refetch.
  const setTheme = useMutation({
    mutationFn: (themeMode: ThemeMode) =>
      apiClient().patch<Preferences, UpdatePreferencesRequest>('/preferences', {
        themeMode,
      }),
    onMutate: (themeMode) => dispatch(themeActions.modeSet(themeMode)),
    onSuccess: (_prefs, themeMode) => {
      queryClient.setQueryData<MeResponse>(['me'], (old) =>
        old
          ? { ...old, preferences: { ...old.preferences, themeMode } }
          : old,
      );
    },
    onError: (_err, _themeMode) => {
      // Persistence failed — fall back to the server's last-known mode so the
      // UI never lies about what the account will see on next boot.
      const server = queryClient.getQueryData<MeResponse>(['me'])?.preferences.themeMode;
      if (server) dispatch(themeActions.modeSet(server));
    },
  });

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="brand">
          SETTINGS
        </Text>
        <Spacer size={2} />
        <Text variant="pageTitle">Account</Text>
        <Spacer size={6} />

        {/* PROFILE — identity summary + the one editable row, grouped under
            one CardHeader instead of a floating identity card + a separate
            caption label (the pre-migration pattern this wave retires). */}
        <Card header={<CardHeader title="Profile" />}>
          <HairlineRowList>
            {me.data ? (
              <View>
                <Text variant="h2">{me.data.profile.displayName}</Text>
                <Spacer size={1} />
                <Text variant="bodySm" color="secondary">
                  {me.data.account.email}
                </Text>
              </View>
            ) : null}
            <SettingsRow
              label="Edit profile"
              description="Display name, headline"
              icon="User"
              accent="amber"
              onPress={() => navigation.navigate('ProfileEdit' as never)}
            />
          </HairlineRowList>
        </Card>

        <Spacer size={6} />
        {/* APPEARANCE stays on the ChoiceTile anatomy deliberately (see the
            module-level note above ChoiceTile usage): each tile is already a
            Card with real typography + token colors, and ChoiceTile is a
            shared onboarding/settings component this wave does not touch. */}
        <Text variant="caption" color="tertiary">
          APPEARANCE
        </Text>
        <Spacer size={2} />
        {THEME_MODES.map((m) => (
          <React.Fragment key={m}>
            <ChoiceTile
              label={THEME_COPY[m].label}
              description={THEME_COPY[m].description}
              selected={mode === m}
              onPress={() => {
                if (mode !== m) setTheme.mutate(m);
              }}
            />
            <Spacer size={2} />
          </React.Fragment>
        ))}

        <Spacer size={4} />
        <Card header={<CardHeader title="Security" sub="AES-256-GCM" />}>
          <HairlineRowList>
            <SettingsRow
              label="Change password"
              icon="KeyRound"
              accent="slateBlue"
              onPress={() => navigation.navigate('ChangePassword' as never)}
            />
            <SettingsRow
              label="Active sessions"
              description="Devices currently signed in"
              icon="MonitorSmartphone"
              accent="slateBlue"
              onPress={() => navigation.navigate('ActiveSessions' as never)}
            />
          </HairlineRowList>
        </Card>
        <Spacer size={2} />
        <View style={styles.footnote}>
          <Icon name="ShieldCheck" size="sm" color="secondary" />
          <Text variant="caption" color="secondary">
            Channel credentials are encrypted with AES-256-GCM
          </Text>
        </View>

        <Spacer size={6} />
        <Card header={<CardHeader title="Alerts" />}>
          <HairlineRowList>
            <SettingsRow
              label="Notification preferences"
              description="Frequency and channels"
              icon="Bell"
              accent="coral"
              onPress={() => navigation.navigate('AlertsSettings' as never)}
            />
          </HairlineRowList>
        </Card>

        <Spacer size={6} />
        <Card header={<CardHeader title="Automation" />}>
          <HairlineRowList>
            <SettingsRow
              label="Automation Hub"
              description="Rules in force and the delivery log"
              icon="Zap"
              accent="amber"
              onPress={() => navigation.navigate('AutomationHub' as never)}
            />
            <SettingsRow
              label="Analytics"
              description="Pipeline metrics, research funnel, publishing"
              icon="BarChart3"
              accent="amber"
              onPress={() => navigation.navigate('Analytics' as never)}
            />
          </HairlineRowList>
        </Card>

        <Spacer size={6} />
        <Card header={<CardHeader title="Sources" />}>
          <HairlineRowList>
            <SettingsRow
              label="Trusted sources"
              description="Enable, disable, and override confidence"
              icon="ListChecks"
              accent="plum"
              onPress={() => navigation.navigate('TrustedSources' as never)}
            />
            <SettingsRow
              label="Source intake"
              description="Connections, sync health, activity"
              icon="Inbox"
              accent="plum"
              onPress={() => navigation.navigate('IntakeHome' as never)}
            />
          </HairlineRowList>
        </Card>

        <Spacer size={6} />
        <Card header={<CardHeader title="Verification" />}>
          <HairlineRowList>
            <SettingsRow
              label="Review queue"
              description="Claims to review and open conflicts"
              icon="ShieldCheck"
              accent="teal"
              onPress={() => navigation.navigate('VerificationQueue' as never)}
            />
          </HairlineRowList>
        </Card>

        <Spacer size={8} />
        <Button
          label="Sign out"
          variant="secondary"
          fullWidth
          onPress={() => dispatch(signout())}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  footnote: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 4,
  },
});
