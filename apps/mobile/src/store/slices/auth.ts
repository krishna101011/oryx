import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { TokenPair } from '@oryx/shared-types';

export type AuthStatus =
  | 'unknown'        // pre-boot
  | 'authenticated'
  | 'unauthenticated'
  | 'refreshing';

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  accountId: string | null;
  sessionId: string | null;
  workspaceId: string | null;     // active workspace; set after first /me
  status: AuthStatus;
  accessTokenExpiresAt: string | null;
}

const initialState: AuthState = {
  accessToken: null,
  refreshToken: null,
  accountId: null,
  sessionId: null,
  workspaceId: null,
  status: 'unknown',
  accessTokenExpiresAt: null,
};

const slice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    tokensSet(state, action: PayloadAction<TokenPair>) {
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.accountId = action.payload.accountId;
      state.sessionId = action.payload.sessionId;
      state.accessTokenExpiresAt = action.payload.accessTokenExpiresAt;
      state.status = 'authenticated';
    },
    accessTokenRefreshed(
      state,
      action: PayloadAction<{ accessToken: string; expiresAt: string }>,
    ) {
      state.accessToken = action.payload.accessToken;
      state.accessTokenExpiresAt = action.payload.expiresAt;
      state.status = 'authenticated';
    },
    refreshing(state) {
      state.status = 'refreshing';
    },
    signedOut(state) {
      state.accessToken = null;
      state.refreshToken = null;
      state.accountId = null;
      state.sessionId = null;
      state.workspaceId = null;
      state.accessTokenExpiresAt = null;
      state.status = 'unauthenticated';
    },
    workspaceSet(state, action: PayloadAction<string>) {
      state.workspaceId = action.payload;
    },
    bootstrapResolved(
      state,
      action: PayloadAction<{ authenticated: boolean }>,
    ) {
      if (state.status === 'unknown') {
        state.status = action.payload.authenticated
          ? 'authenticated'
          : 'unauthenticated';
      }
    },
  },
});

export const authActions = slice.actions;
export const authReducer = slice.reducer;
