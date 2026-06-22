import React from 'react';
import { ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Card, Screen, Spacer, Text, Button } from '@oryx/design-system';
import { useMe } from '../../../hooks/useMe';
import { useAppDispatch } from '../../../store';
import { signout } from '../../../store/thunks/auth';
import { SettingsRow } from '../components/SettingsRow';

export const SettingsHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const me = useMe();

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="brand">
          SETTINGS
        </Text>
        <Spacer size={2} />
        <Text variant="display">Account</Text>
        <Spacer size={6} />

        {me.data ? (
          <Card variant="elevated">
            <Text variant="h2">{me.data.profile.displayName}</Text>
            <Spacer size={1} />
            <Text variant="bodySm" color="secondary">
              {me.data.account.email}
            </Text>
          </Card>
        ) : null}

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          PROFILE
        </Text>
        <Spacer size={2} />
        <SettingsRow
          label="Edit profile"
          description="Display name, headline"
          icon="User"
          accent="teal"
          onPress={() => navigation.navigate('ProfileEdit' as never)}
        />

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          SECURITY
        </Text>
        <Spacer size={2} />
        <SettingsRow
          label="Change password"
          icon="KeyRound"
          accent="indigo"
          onPress={() => navigation.navigate('ChangePassword' as never)}
        />
        <Spacer size={2} />
        <SettingsRow
          label="Active sessions"
          description="Devices currently signed in"
          icon="MonitorSmartphone"
          accent="indigo"
          onPress={() => navigation.navigate('ActiveSessions' as never)}
        />

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          ALERTS
        </Text>
        <Spacer size={2} />
        <SettingsRow
          label="Notification preferences"
          description="Frequency and channels"
          icon="Bell"
          accent="blue"
          onPress={() => navigation.navigate('AlertsSettings' as never)}
        />

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          SOURCES
        </Text>
        <Spacer size={2} />
        <SettingsRow
          label="Trusted sources"
          description="Enable, disable, and override confidence"
          icon="ListChecks"
          accent="violet"
          onPress={() => navigation.navigate('TrustedSources' as never)}
        />
        <Spacer size={2} />
        <SettingsRow
          label="Source intake"
          description="Connections, sync health, activity"
          icon="Inbox"
          accent="violet"
          onPress={() => navigation.navigate('IntakeHome' as never)}
        />

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          VERIFICATION
        </Text>
        <Spacer size={2} />
        <SettingsRow
          label="Review queue"
          description="Claims to review and open conflicts"
          icon="ShieldCheck"
          accent="teal"
          onPress={() => navigation.navigate('VerificationQueue' as never)}
        />

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
