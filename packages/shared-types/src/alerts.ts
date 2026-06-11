import type { Id, Timestamp } from './common';
import type { ActivityType } from './activity';
import type { DevicePlatform } from './sessions';
import type { NotificationFrequency } from './preferences';

export type Channel = 'in_app' | 'push' | 'email';

export interface QuietHours {
  start: string; // 'HH:mm'
  end: string;
  tz: string; // IANA
}

export interface AlertPreference {
  type: ActivityType;
  channel: Channel;
  frequency: NotificationFrequency;
  quietHours: QuietHours | null;
}

export interface UpdateAlertPreferenceRequest {
  frequency?: NotificationFrequency;
  quietHours?: QuietHours | null;
}

export interface AlertDevice {
  id: Id;
  platform: DevicePlatform;
  appVersion: string | null;
  lastSeenAt: Timestamp;
}

export interface RegisterAlertDeviceRequest {
  platform: DevicePlatform;
  pushToken: string;
  appVersion?: string;
}
