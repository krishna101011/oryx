import type { ApiError, ApiResponse } from '@anant/shared-types';
import { AppApiError } from '../errors';
import { logger } from '../logger';

const DEFAULT_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/v1';

export type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export interface ApiClientConfig {
  baseUrl?: string;
  getAccessToken: () => string | null;
  getWorkspaceId: () => string | null;
  /**
   * Called on AUTH_TOKEN_EXPIRED. Must return the new access token or null
   * to indicate refresh failed (in which case the client throws and the
   * caller should sign out).
   */
  refreshAccessToken: () => Promise<string | null>;
}

function requestId(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Typed API client.
 *
 * - Attaches bearer + X-Workspace-Id + X-Request-Id
 * - On AUTH_TOKEN_EXPIRED: refresh once via refreshAccessToken(), retry once
 * - Unwraps ApiResponse envelope; surfaces ApiError as AppApiError
 */
export class ApiClient {
  private readonly baseUrl: string;
  private readonly cfg: ApiClientConfig;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl ?? DEFAULT_BASE_URL;
    this.cfg = config;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }
  /**
   * Like get(), but returns the full envelope so callers can read
   * meta.pagination — the CR-9 cursor contract on Phase 3 operational lists.
   */
  async getEnvelope<T>(path: string): Promise<ApiResponse<T>> {
    return this.requestEnvelope<T>('GET', path);
  }
  post<T, B = unknown>(path: string, body?: B): Promise<T> {
    return this.request<T>('POST', path, body);
  }
  patch<T, B = unknown>(path: string, body?: B): Promise<T> {
    return this.request<T>('PATCH', path, body);
  }
  put<T, B = unknown>(path: string, body?: B): Promise<T> {
    return this.request<T>('PUT', path, body);
  }
  delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  private buildHeaders(rid: string, token: string | null): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Request-Id': rid,
    };
    const wsp = this.cfg.getWorkspaceId();
    if (wsp) headers['X-Workspace-Id'] = wsp;
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }

  private async doFetch(
    method: Method,
    path: string,
    body: unknown,
    token: string | null,
    rid: string,
  ): Promise<Response> {
    const init: RequestInit = {
      method,
      headers: this.buildHeaders(rid, token),
    };
    if (body !== undefined) init.body = JSON.stringify(body);
    return fetch(`${this.baseUrl}${path}`, init);
  }

  private async request<T>(
    method: Method,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const envelope = await this.requestEnvelope<T>(method, path, body);
    return envelope.data;
  }

  private async requestEnvelope<T>(
    method: Method,
    path: string,
    body?: unknown,
  ): Promise<ApiResponse<T>> {
    const rid = requestId();
    let token = this.cfg.getAccessToken();
    let res = await this.doFetch(method, path, body, token, rid);

    // Refresh dance: one retry on AUTH_TOKEN_EXPIRED.
    if (res.status === 401) {
      const clone = await this.peekErrorCode(res);
      if (clone === 'AUTH_TOKEN_EXPIRED') {
        const refreshed = await this.cfg.refreshAccessToken();
        if (refreshed) {
          token = refreshed;
          res = await this.doFetch(method, path, body, token, rid);
        }
      }
    }

    const text = await res.text();
    const parsed =
      text.length > 0 ? (JSON.parse(text) as ApiResponse<T> | ApiError) : undefined;

    if (!res.ok) {
      if (parsed && typeof parsed === 'object' && 'error' in parsed) {
        const err = (parsed as ApiError).error;
        logger.warn('api.error', { code: err.code, status: res.status, path });
        throw new AppApiError({
          code: err.code,
          message: err.message,
          httpStatus: res.status,
          requestId: err.requestId,
          ...(err.details !== undefined ? { details: err.details } : {}),
        });
      }
      throw new AppApiError({
        code: 'INTERNAL_ERROR',
        message: `HTTP ${res.status}`,
        httpStatus: res.status,
        requestId: rid,
      });
    }

    if (parsed && typeof parsed === 'object' && 'data' in parsed) {
      return parsed as ApiResponse<T>;
    }
    return { data: parsed as T };
  }

  // Read the error envelope without consuming the response body.
  private async peekErrorCode(res: Response): Promise<string | null> {
    try {
      const clone = res.clone();
      const text = await clone.text();
      if (!text) return null;
      const parsed = JSON.parse(text) as ApiError;
      return parsed?.error?.code ?? null;
    } catch {
      return null;
    }
  }
}

// ---------------------------------------------------------------------------
// Default singleton, wired by `providers/AppProviders.tsx` once the store is up.
// ---------------------------------------------------------------------------

let _client: ApiClient | null = null;

export function configureApiClient(config: ApiClientConfig): ApiClient {
  _client = new ApiClient(config);
  return _client;
}

export function apiClient(): ApiClient {
  if (!_client) {
    throw new Error('ApiClient not configured — call configureApiClient first');
  }
  return _client;
}
