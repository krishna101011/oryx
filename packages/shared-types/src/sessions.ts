import type { Id, Timestamp } from './common';

export type DevicePlatform = 'ios' | 'android' | 'web';

export interface Session {
  id: Id;
  deviceLabel: string;
  devicePlatform: DevicePlatform;
  createdAt: Timestamp;
  lastUsedAt: Timestamp;
  expiresAt: Timestamp;
  current: boolean;
}
