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
  PlanBilling: undefined;
  // Deep-link target for the invite email — token identifies which invite.
  // Team promotion wave (2026-07-26): Members moved out to its own top-level
  // Team tab (see TeamStackParamList) — this is the only Team-related route
  // left in Settings, since the invite link itself is unrelated to that nav
  // change and stays reachable from wherever the user currently is.
  AcceptInvite: { token: string };
  TrustedSources: undefined;
  // Phase 3 intake module — entered via Settings → Sources (§15.4)
  IntakeHome: undefined;
  IntakeSourceManagement: undefined;
  IntakeSourceDetail: { sourceId: string };
  IntakeHealth: undefined;
  IntakeActivity: { sourceId?: string } | undefined;
  // One ingested item's real content (2026-07-12) — opened from an Activity
  // "New item ingested" row, a Dashboard "Today" row, and web search results.
  // `origin` is set only by the Activity entry point (2026-07-25) so back
  // navigation can return to Activity instead of the Settings stack it was
  // pushed onto — see ItemDetailScreen's beforeRemove handling.
  IntakeItemDetail: { itemId: string; origin?: 'activity' };
  ManualIngest: undefined;
  // Phase 4 Wave C — per-source credibility (ADR-031), keyed by intake source id
  SourceCredibility: { sourceId: string };
  // Phase 4 Wave D — analyst review queue + conflict resolution
  VerificationQueue: undefined;
  ConflictReview: { conflictId: string };
  // Phase 4 Wave E — claim + intelligence object detail
  ClaimDetail: { claimId: string };
  IntelligenceObjectDetail: { objectId: string };
  // Phase 6 Wave B — Automation Hub (Rules + Log)
  AutomationHub: undefined;
  // Phase 7 Wave B — Analytics dashboard (Overview + Research + Publishing)
  Analytics: undefined;
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

// Team promotion wave (2026-07-26) — Team is now its own top-level tab
// (previously Settings > Members). TeamHome carries the real member list +
// invite form (moved verbatim from the old MembersScreen); TeamActivity is
// the real activity feed (invited/joined/removed events). TeamChat (Team
// Chat foundation wave, 2026-07-27) is the single-channel workspace chat.
export type TeamStackParamList = {
  TeamHome: undefined;
  TeamActivity: undefined;
  TeamChat: undefined;
};

// Phase 5 Wave A — content tab stack
export type ContentStackParamList = {
  ContentHome: undefined;
  GenerateDraft: undefined;
  DraftEditor: { draftId: string };
  // Phase 5 Wave C — drafts awaiting review
  ReviewQueue: undefined;
  // Phase 5 Wave D — publish targets + delivery history
  PublishTargets: undefined;
  PublishHistory: undefined;
  // Phase 5 Wave E — content calendar
  Calendar: undefined;
};

// Phase 8 Wave C — Academy is its own top-level tab (the LEARN sidebar
// group's real, activated entry), same shape as Research/Content/Team:
// a course list root plus a lesson-detail screen, courseId carried through
// so the viewer can invalidate that course's real progress on completion.
export type AcademyStackParamList = {
  AcademyHome: undefined;
  // courseId is deliberately NOT a param — LessonDetail's own response
  // already carries it, so the viewer derives it from data instead of
  // duplicating it in the route (and it stays deep-link-safe with just
  // a lessonId in the URL).
  LessonViewer: { lessonId: string };
};

export type RootTabParamList = {
  Home: undefined;
  Research: NavigatorScreenParams<ResearchStackParamList> | undefined;
  Content: NavigatorScreenParams<ContentStackParamList> | undefined;
  Team: NavigatorScreenParams<TeamStackParamList> | undefined;
  Academy: NavigatorScreenParams<AcademyStackParamList> | undefined;
  Activity: undefined;
  Settings: NavigatorScreenParams<SettingsStackParamList> | undefined;
};

export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Onboarding: NavigatorScreenParams<OnboardingStackParamList>;
  Tabs: NavigatorScreenParams<RootTabParamList>;
  // Public Reader Rev 1 — genuinely unauthenticated, reachable regardless of
  // auth.status (see RootNavigator's public-route branch). `slug` comes from
  // the URL via linking.ts's top-level 'public/pages/:slug' entry.
  PublicPage: { slug: string };
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
