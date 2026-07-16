import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import type { MeResponse } from '@oryx/shared-types';
import { apiClient } from '../lib/api/client';
import { isApiError } from '../lib/errors';
import { useAppDispatch, useAppSelector } from '../store';
import { authActions } from '../store/slices/auth';
import { themeActions } from '../store/slices/theme';

/**
 * Bootstrap query: pulls account + profile + workspace + preferences + flags + onboarding.
 *
 * Side effects:
 * - On success, writes the active workspace id back into Redux so subsequent
 *   API calls can attach X-Workspace-Id.
 * - On a terminal auth error (AUTH_REQUIRED after the client-side refresh
 *   interceptor has already failed), dispatches signedOut so the user is
 *   routed to AuthStack instead of being stuck on a splash.
 */
export function useMe() {
  const dispatch = useAppDispatch();
  const status = useAppSelector((s) => s.auth.status);
  const query = useQuery<MeResponse>({
    queryKey: ['me'],
    queryFn: () => apiClient().get<MeResponse>('/auth/me'),
    enabled: status === 'authenticated',
    staleTime: 60 * 1000,
    // Feature flags live in this payload; without this, a flag flipped
    // server-side stays stale for the entire session a tab is left open.
    // Scoped override (global default is false): refetch when the user
    // returns to the app. react-query gates this on staleTime above, so
    // rapid tab-switching within 60s won't spam /auth/me.
    refetchOnWindowFocus: true,
    retry: (failureCount, error) => {
      // Don't retry terminal auth errors — sign-out is the correct response.
      if (isApiError(error)) {
        if (
          error.code === 'AUTH_REQUIRED' ||
          error.code === 'AUTH_REFRESH_INVALID' ||
          error.code === 'AUTH_REFRESH_REUSE_DETECTED'
        ) {
          return false;
        }
      }
      return failureCount < 2;
    },
  });

  useEffect(() => {
    if (query.data?.workspace.id) {
      dispatch(authActions.workspaceSet(query.data.workspace.id));
    }
  }, [query.data?.workspace.id, dispatch]);

  // Theming Phase A: the account-synced mode hydrates from the same payload.
  // The Settings toggle also writes the ['me'] cache on success, so this
  // effect never fights an in-flight local switch with stale server data.
  // Deep optional chain on purpose: rendered tests seed ['me'] with partial
  // payloads (workspace + flags only), and the query cache is a shared
  // namespace — never assume another writer supplied the full shape.
  const themeMode = query.data?.preferences?.themeMode;
  useEffect(() => {
    if (themeMode) {
      dispatch(themeActions.modeSet(themeMode));
    }
  }, [themeMode, dispatch]);

  useEffect(() => {
    if (!query.error) return;
    if (
      isApiError(query.error) &&
      (query.error.code === 'AUTH_REQUIRED' ||
        query.error.code === 'AUTH_REFRESH_INVALID' ||
        query.error.code === 'AUTH_REFRESH_REUSE_DETECTED')
    ) {
      dispatch(authActions.signedOut());
    }
  }, [query.error, dispatch]);

  return query;
}
