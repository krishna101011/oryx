import type { Id, Timestamp } from './common';

export type Focus = 'markets' | 'crypto' | 'both';
export type ContentStyle = 'concise' | 'balanced' | 'detailed';
export type VerificationStrictness = 'loose' | 'balanced' | 'strict';
export type NotificationFrequency = 'off' | 'instant' | 'daily' | 'weekly';
// Theming Phase A (2026-07-16): account-synced light/dark mode.
export type ThemeMode = 'dark' | 'light';

export interface Preferences {
  accountId: Id;
  focus: Focus;
  contentStyle: ContentStyle;
  verificationStrictness: VerificationStrictness;
  notificationFrequency: NotificationFrequency;
  themeMode: ThemeMode;
  customTopics: string[];
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface UpdatePreferencesRequest {
  focus?: Focus;
  contentStyle?: ContentStyle;
  verificationStrictness?: VerificationStrictness;
  notificationFrequency?: NotificationFrequency;
  themeMode?: ThemeMode;
  customTopics?: string[];
}
