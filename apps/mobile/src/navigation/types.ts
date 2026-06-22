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
  // Phase 4 Wave D — analyst review queue + conflict resolution
  VerificationQueue: undefined;
  ConflictReview: { conflictId: string };
  // Phase 4 Wave E — claim + intelligence object detail
  ClaimDetail: { claimId: string };
  IntelligenceObjectDetail: { objectId: string };
};

// Phase 4 Wave E — research tab stack
export type ResearchStackParamList = {
  ResearchWorkspaceList: undefined;
  ResearchWorkspaceDetail: { rwsId: string };
  IntelligenceObjectPicker: { rwsId: string; workspaceName: string };
  ResearchPacket: { packetId: string };
  IntelligenceObjectDetail: { objectId: string };
  ClaimDetail: { claimId: string };
};

// Phase 5 Wave A — content tab stack
export type ContentStackParamList = {
  ContentHome: undefined;
  GenerateDraft: undefined;
  DraftEditor: { draftId: string };
  // Phase 5 Wave C — drafts awaiting review
  ReviewQueue: undefined;
};

export type RootTabParamList = {
  Home: undefined;
  Research: NavigatorScreenParams<ResearchStackParamList> | undefined;
  Content: NavigatorScreenParams<ContentStackParamList> | undefined;
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
