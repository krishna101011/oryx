import type { Id, Timestamp } from './common';

export interface Profile {
  accountId: Id;
  displayName: string;
  avatarUrl: string | null;
  headline: string | null;
  timezone: string; // IANA
  locale: string; // BCP-47
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface UpdateProfileRequest {
  displayName?: string;
  avatarUrl?: string | null;
  headline?: string | null;
  timezone?: string;
  locale?: string;
}
