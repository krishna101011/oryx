import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useTheme } from '@oryx/design-system';
import type { SettingsStackParamList } from './types';
import { useMe } from '../hooks/useMe';
import { SettingsHomeScreen } from '../modules/settings/screens/SettingsHomeScreen';
import { ProfileEditScreen } from '../modules/settings/screens/ProfileEditScreen';
import { ChangePasswordScreen } from '../modules/settings/screens/ChangePasswordScreen';
import { ActiveSessionsScreen } from '../modules/settings/screens/ActiveSessionsScreen';
import { AlertsSettingsScreen } from '../modules/settings/screens/AlertsSettingsScreen';
import { PlanBillingScreen } from '../modules/settings/screens/PlanBillingScreen';
import { TrustedSourcesScreen } from '../modules/settings/screens/TrustedSourcesScreen';
import { IntakeHomeScreen } from '../modules/intake/screens/IntakeHomeScreen';
import { SourceManagementScreen } from '../modules/intake/screens/SourceManagementScreen';
import { SourceDetailScreen } from '../modules/intake/screens/SourceDetailScreen';
import { IntakeHealthScreen } from '../modules/intake/screens/IntakeHealthScreen';
import { IntakeActivityScreen } from '../modules/intake/screens/IntakeActivityScreen';
import { ItemDetailScreen } from '../modules/intake/screens/ItemDetailScreen';
import { ManualIngestScreen } from '../modules/intake/screens/ManualIngestScreen';
import { SourceCredibilityScreen } from '../modules/verification/screens/SourceCredibilityScreen';
import { VerificationQueueScreen } from '../modules/verification/screens/VerificationQueueScreen';
import { ConflictReviewScreen } from '../modules/verification/screens/ConflictReviewScreen';
import { ClaimDetailScreen } from '../modules/verification/screens/ClaimDetailScreen';
import { IntelligenceObjectDetailScreen } from '../modules/verification/screens/IntelligenceObjectDetailScreen';
import { AutomationHubScreen } from '../modules/automation/screens/AutomationHubScreen';
import { AnalyticsHomeScreen } from '../modules/analytics/screens/AnalyticsHomeScreen';

const Stack = createNativeStackNavigator<SettingsStackParamList>();

export const SettingsStack: React.FC = () => {
  const me = useMe();
  const t = useTheme();
  // §15.2 — the ManualIngest route is MOUNTED only for platform admins.
  // Workspace admins/owners/editors/readers never see the surface.
  const isPlatformAdmin = me.data?.account.isPlatformAdmin ?? false;
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: t.colors.bg.primary },
        headerTintColor: t.colors.text.primary,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <Stack.Screen name="SettingsHome" component={SettingsHomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="ProfileEdit" component={ProfileEditScreen} options={{ title: 'Profile' }} />
      <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} options={{ title: 'Password' }} />
      <Stack.Screen name="ActiveSessions" component={ActiveSessionsScreen} options={{ title: 'Sessions' }} />
      <Stack.Screen name="AlertsSettings" component={AlertsSettingsScreen} options={{ title: 'Alerts' }} />
      <Stack.Screen name="PlanBilling" component={PlanBillingScreen} options={{ title: 'Plan' }} />
      <Stack.Screen name="TrustedSources" component={TrustedSourcesScreen} options={{ title: 'Sources' }} />
      <Stack.Screen name="IntakeHome" component={IntakeHomeScreen} options={{ title: 'Intake' }} />
      <Stack.Screen name="IntakeSourceManagement" component={SourceManagementScreen} options={{ title: 'Manage' }} />
      <Stack.Screen name="IntakeSourceDetail" component={SourceDetailScreen} options={{ title: 'Source' }} />
      <Stack.Screen name="SourceCredibility" component={SourceCredibilityScreen} options={{ title: 'Credibility' }} />
      <Stack.Screen name="VerificationQueue" component={VerificationQueueScreen} options={{ title: 'Review queue' }} />
      <Stack.Screen name="ConflictReview" component={ConflictReviewScreen} options={{ title: 'Resolve conflict' }} />
      <Stack.Screen name="ClaimDetail" component={ClaimDetailScreen} options={{ title: 'Claim' }} />
      <Stack.Screen name="IntelligenceObjectDetail" component={IntelligenceObjectDetailScreen} options={{ title: 'Object' }} />
      <Stack.Screen name="AutomationHub" component={AutomationHubScreen} options={{ title: 'Automation Hub' }} />
      <Stack.Screen name="Analytics" component={AnalyticsHomeScreen} options={{ title: 'Analytics' }} />
      <Stack.Screen name="IntakeHealth" component={IntakeHealthScreen} options={{ title: 'Health' }} />
      <Stack.Screen name="IntakeActivity" component={IntakeActivityScreen} options={{ title: 'Activity' }} />
      <Stack.Screen name="IntakeItemDetail" component={ItemDetailScreen} options={{ title: 'Item' }} />
      {isPlatformAdmin ? (
        <Stack.Screen name="ManualIngest" component={ManualIngestScreen} options={{ title: 'Manual ingest' }} />
      ) : null}
    </Stack.Navigator>
  );
};
