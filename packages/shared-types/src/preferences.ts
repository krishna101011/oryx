import type { Id, Timestamp } from './common';

export type Focus = 'markets' | 'crypto' | 'both';
export type ContentStyle = 'concise' | 'balanced' | 'detailed';
export type VerificationStrictness = 'loose' | 'balanced' | 'strict';
export type NotificationFrequency = 'off' | 'instant' | 'daily' | 'weekly';

export interface Preferences {
  accountId: Id;
  focus: Focus;
  contentStyle: ContentStyle;
  verificationStrictness: VerificationStrictness;
  notificationFrequency: NotificationFrequency;
  customTopics: string[];
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface UpdatePreferencesRequest {
  focus?: Focus;
  contentStyle?: ContentStyle;
  verificationStrictness?: VerificationStrictness;
  notificationFrequency?: NotificationFrequency;
  customTopics?: string[];
}
