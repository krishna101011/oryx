import type { Id, Timestamp } from './common';

export type AccountStatus = 'pending' | 'active' | 'suspended' | 'deleted';

/** Canonical identity record. Returned in /v1/auth/me. */
export interface Account {
  id: Id;
  email: string;
  status: AccountStatus;
  emailVerified: boolean;
  /** Operator flag (§17.4 intake.platform). Gates ManualIngestScreen (§15.2). */
  isPlatformAdmin: boolean;
  createdAt: Timestamp;
}
