/**
 * Common envelope types shared by every domain.
 *
 * Source of truth for the FE/BE contract.
 * Backend pydantic mirror is GENERATED from this file. Edit here and run
 * `pnpm gen:pydantic`. CI rejects drift.
 */

export type Id = string;
export type Timestamp = string; // ISO 8601
export type Cursor = string;

export interface Pagination {
  nextCursor: Cursor | null;
  prevCursor: Cursor | null;
}

export interface ResponseMeta {
  requestId: string;
  serverTime: Timestamp;
  pagination?: Pagination;
}

export interface ApiResponse<T> {
  data: T;
  meta?: ResponseMeta;
}

export interface ApiError {
  error: {
    code: ErrorCode;
    message: string;
    details?: Record<string, unknown>;
    requestId: string;
  };
}

/**
 * Stable, machine-readable error codes.
 * Phase 2 set — additive only; never rename.
 */
export type ErrorCode =
  // generic
  | 'INTERNAL_ERROR'
  | 'NOT_FOUND'
  | 'VALIDATION_FAILED'
  | 'RATE_LIMITED'
  | 'NOT_IMPLEMENTED'
  | 'PROVIDER_ERROR'
  // auth
  | 'AUTH_REQUIRED'
  | 'AUTH_INVALID_CREDENTIALS'
  | 'AUTH_TOKEN_EXPIRED'
  | 'AUTH_REFRESH_INVALID'
  | 'AUTH_REFRESH_REUSE_DETECTED'
  | 'AUTH_EMAIL_TAKEN'
  | 'AUTH_PASSWORD_WEAK'
  | 'AUTH_RATE_LIMITED'
  | 'AUTH_ACCOUNT_LOCKED'
  | 'AUTH_MFA_REQUIRED'
  | 'AUTH_MFA_INVALID'
  // workspace / permissions
  | 'PERMISSION_DENIED'
  | 'FEATURE_DISABLED'
  | 'WORKSPACE_NOT_FOUND'
  | 'ONBOARDING_REQUIRED'
  // billing
  | 'PAYMENT_PROVIDER_UNAVAILABLE';

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down';
  service: string;
  environment: 'dev' | 'staging' | 'prod';
  serverTime: Timestamp;
}

export interface BuildInfo {
  version: string;
  commit: string;
  builtAt: Timestamp;
}
