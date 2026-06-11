import type { LinkingOptions } from '@react-navigation/native';

export const linking: LinkingOptions<ReactNavigation.RootParamList> = {
  prefixes: ['anantcapital://'],
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
              TrustedSources: 'settings/sources',
            },
          },
        },
      },
    },
  },
};
