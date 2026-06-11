import type { ErrorCode } from '@anant/shared-types';

export class AppApiError extends Error {
  readonly code: ErrorCode;
  readonly httpStatus: number;
  readonly requestId: string;
  readonly details?: Record<string, unknown>;

  constructor(args: {
    code: ErrorCode;
    message: string;
    httpStatus: number;
    requestId: string;
    details?: Record<string, unknown>;
  }) {
    super(args.message);
    this.name = 'AppApiError';
    this.code = args.code;
    this.httpStatus = args.httpStatus;
    this.requestId = args.requestId;
    if (args.details !== undefined) this.details = args.details;
  }
}

export const isApiError = (e: unknown): e is AppApiError =>
  e instanceof AppApiError;
