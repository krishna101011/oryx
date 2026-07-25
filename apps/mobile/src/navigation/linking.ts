import type { LinkingOptions } from '@react-navigation/native';

export const linking: LinkingOptions<ReactNavigation.RootParamList> = {
  prefixes: ['oryx://'],
  config: {
    screens: {
      Auth: {
        screens: {
          SignIn: 'auth/sign-in',
          SignUp: 'auth/sign-up',
          ForgotPassword: 'auth/forgot',
          // Deep-link target for password reset emails (Phase 6 activates real flow).
          ResetPassword: 'auth/reset/:token?',
        },
      },
      Onboarding: {
        screens: {
          Welcome: 'onboarding/welcome',
          FocusAndSources: 'onboarding/focus',
          NotificationsAndPermissions: 'onboarding/notifications',
          StyleAndStrictness: 'onboarding/style',
        },
      },
      Tabs: {
        screens: {
          Home: 'home',
          Research: 'research/:id?',
          Content: 'content/:id?',
          Activity: 'activity',
          Settings: {
            screens: {
              SettingsHome: 'settings',
              ProfileEdit: 'settings/profile',
              ChangePassword: 'settings/password',
              ActiveSessions: 'settings/sessions',
              AlertsSettings: 'settings/alerts',
              PlanBilling: 'settings/plan',
              TrustedSources: 'settings/sources',
              AutomationHub: 'settings/automation',
              Analytics: 'settings/analytics',
              // Source-governance wave (2026-07-22): these screens already
              // existed and were already wired via in-app navigate() calls,
              // but had no web URL at all (confirmed: zero Intake entries
              // existed here beforehand) — the whole intake sub-area was
              // unreachable on web except by a live in-app tap chain that
              // itself starts from a not-yet-wired sidebar item. Registering
              // the exact existing screens here (no new screens, no new
              // navigation logic) makes them reachable for direct
              // verification, matching every other Settings sub-screen's
              // existing pattern one-for-one.
              IntakeHome: 'settings/intake',
              IntakeSourceManagement: 'settings/intake/manage',
              IntakeSourceDetail: 'settings/intake/source/:sourceId',
              SourceCredibility: 'settings/intake/source/:sourceId/credibility',
            },
          },
        },
      },
    },
  },
};
