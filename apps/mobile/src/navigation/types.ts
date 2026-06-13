import type { NavigatorScreenParams } from '@react-navigation/native';

export type AuthStackParamList = {
  SignIn: undefined;
  SignUp: undefined;
  ForgotPassword: undefined;
  ResetPassword: { token?: string } | undefined;
};

export type OnboardingStackParamList = {
  Welcome: undefined;
  FocusAndSources: undefined;
  NotificationsAndPermissions: undefined;
  StyleAndStrictness: undefined;
};

export type SettingsStackParamList = {
  SettingsHome: undefined;
  ProfileEdit: undefined;
  ChangePassword: undefined;
  ActiveSessions: undefined;
  AlertsSettings: undefined;
  TrustedSources: undefined;
  // Phase 3 intake module — entered via Settings → Sources (§15.4)
  IntakeHome: undefined;
  IntakeSourceManagement: undefined;
  IntakeSourceDetail: { sourceId: string };
  IntakeHealth: undefined;
  IntakeActivity: { sourceId?: string } | undefined;
  ManualIngest: undefined;
  // Phase 4 Wave C — per-source credibility (ADR-031), keyed by intake source id
  SourceCredibility: { sourceId: string };
};

export type RootTabParamList = {
  Home: undefined;
  Research: { id?: string } | undefined;
  Content: { id?: string } | undefined;
  Activity: undefined;
  Settings: NavigatorScreenParams<SettingsStackParamList> | undefined;
};

export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Onboarding: NavigatorScreenParams<OnboardingStackParamList>;
  Tabs: NavigatorScreenParams<RootTabParamList>;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
