import type { Id, Timestamp } from './common';
import type { Account } from './accounts';
import type { Profile } from './profiles';
import type { ActiveWorkspace } from './workspaces';
import type { Preferences } from './preferences';
import type { FlagSet } from './feature-flags';
import type {
  OnboardingState,
  OnboardingStep,
} from './onboarding';
import type { DevicePlatform } from './sessions';

// ---- Requests ----

export interface SignupRequest {
  email: string;
  password: string;
  displayName: string;
  deviceId: string;
  deviceLabel: string;
  devicePlatform: DevicePlatform;
}

export interface SigninRequest {
  email: string;
  password: string;
  deviceId: string;
  deviceLabel: string;
  devicePlatform: DevicePlatform;
}

export interface RefreshRequest {
  refreshToken: string;
  deviceId: string;
}

/** Team/Workspace Rev 2 §4 — switching reuses the refresh-token mechanism;
 * real membership in workspaceId is re-verified server-side before a new
 * token pair is minted. */
export interface SwitchWorkspaceRequest {
  refreshToken: string;
  deviceId: string;
  workspaceId: Id;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  newPassword: string;
}

// ---- Responses ----

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  accessTokenExpiresAt: Timestamp;
  refreshTokenExpiresAt: Timestamp;
  sessionId: Id;
  accountId: Id;
}

export interface SignupResponse {
  tokens: TokenPair;
  account: Account;
}

export interface SigninResponse {
  tokens: TokenPair;
  account: Account;
}

/**
 * Single bootstrap envelope for the mobile app on cold boot.
 * Composed by /v1/auth/me from multiple services.
 */
export interface MeResponse {
  account: Account;
  profile: Profile;
  workspace: ActiveWorkspace;
  preferences: Preferences;
  activity: { unreadCount: number };
  flags: FlagSet;
  onboarding: {
    state: OnboardingState;
    nextStep: OnboardingStep | null;
  };
  // Phase 4 Wave E — analyst workload + research surface counts.
  verification: {
    pendingReviewCount: number;
    openConflictCount: number;
    // 2026-07-11 — Command Center VERIFIED stat: intelligence objects with
    // verification_status 'verified' or 'analyst_approved' (approval replaces
    // 'verified', so both statuses mean verified).
    verifiedCount: number;
  };
  research: {
    activeWorkspaceCount: number;
    readyPacketCount: number;
  };
  // Phase 5 Wave A — content workload counts (current workspace).
  content: {
    draftCount: number;
    pendingReviewCount: number;
    scheduledCount: number;
    publishedThisWeek: number;
  };
  serverTime: Timestamp;
  build: { version: string; commit: string };
}

// ---- MFA contracts (interface only in Phase 2 — endpoints return 501) ----

export interface MfaSetupResponse {
  secret: string;
  otpauthUrl: string;
}

export interface MfaVerifyRequest {
  code: string;
}
