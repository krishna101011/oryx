import React, { useEffect, useMemo } from 'react';
import { Provider as ReduxProvider, useSelector, useStore } from 'react-redux';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, themes } from '@oryx/design-system';
import { store, type RootState } from '../store';
import { QueryProvider } from './QueryProvider';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { configureApiClient } from '../lib/api/client';
import { refreshAccess } from '../store/thunks/auth';

/**
 * Wires up the API client against the live store so the bearer + workspace
 * headers and the refresh interceptor read straight from Redux.
 */
const ApiClientInit: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const reduxStore = useStore<RootState>();

  // useMemo so we configure once on mount; the closures read live state on each call.
  useMemo(() => {
    configureApiClient({
      getAccessToken: () => reduxStore.getState().auth.accessToken,
      getWorkspaceId: () => reduxStore.getState().auth.workspaceId,
      refreshAccessToken: refreshAccess(
        () => reduxStore.getState().auth.refreshToken,
        reduxStore.dispatch,
      ),
    });
  }, [reduxStore]);

  return <>{children}</>;
};

const BootstrapAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const reduxStore = useStore<RootState>();
  useEffect(() => {
    // Lazy-import so we don't pull the thunk into the providers chunk at parse time.
    void import('../store/thunks/auth').then(({ bootstrapAuth }) => {
      reduxStore.dispatch(bootstrapAuth() as unknown as never);
    });
  }, [reduxStore]);
  return <>{children}</>;
};

/**
 * Theming Phase A: ThemeProvider's `theme` prop is driven by the Redux theme
 * slice (hydrated from /auth/me preferences, toggled in Settings). Must sit
 * inside ReduxProvider; ErrorBoundary stays OUTSIDE ThemeProvider by design —
 * it must render even when the theme system itself is what broke.
 */
const ThemedProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const mode = useSelector((s: RootState) => s.theme.mode);
  return <ThemeProvider theme={themes[mode]}>{children}</ThemeProvider>;
};

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <ErrorBoundary>
    <ReduxProvider store={store}>
      <ApiClientInit>
        <BootstrapAuth>
          <QueryProvider>
            <SafeAreaProvider>
              <ThemedProvider>{children}</ThemedProvider>
            </SafeAreaProvider>
          </QueryProvider>
        </BootstrapAuth>
      </ApiClientInit>
    </ReduxProvider>
  </ErrorBoundary>
);
