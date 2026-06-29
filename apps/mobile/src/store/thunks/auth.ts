import { Platform } from 'react-native';
import type {
  RefreshRequest,
  SigninRequest,
  SignupRequest,
  TokenPair,
  SigninResponse,
  SignupResponse,
} from '@oryx/shared-types';
import { apiClient } from '../../lib/api/client';
import { getDeviceId, getDeviceLabel, getDevicePlatform } from '../../lib/device';
import { logger } from '../../lib/logger';
import {
  SecureKeys,
  clearAllSecrets,
  secureDelete,
  secureGet,
  secureSet,
} from '../../lib/secure-store';
import { authActions } from '../slices/auth';
import type { AppDispatch } from '..';

async function persistTokens(t: TokenPair): Promise<void> {
  await Promise.all([
    secureSet(SecureKeys.accessToken, t.accessToken),
    secureSet(SecureKeys.refreshToken, t.refreshToken),
    secureSet(SecureKeys.accountId, t.accountId),
  ]);
}

export const bootstrapAuth = () => async (dispatch: AppDispatch): Promise<void> => {
  // Web: the session lives in an httpOnly cookie the JS layer cannot read by
  // design, so there is nothing to restore from storage. The cookie IS the
  // persistence — probe /me with credentials (the client sends them on web).
  // 200 means the browser still holds a valid session; anything else → signed
  // out. This is what survives a hard page reload.
  if (Platform.OS === 'web') {
    try {
      await apiClient().get('/auth/me');
      dispatch(authActions.bootstrapResolved({ authenticated: true }));
    } catch {
      dispatch(authActions.bootstrapResolved({ authenticated: false }));
    }
    return;
  }

  // Native: restore tokens from device secure storage (Keychain / EncryptedSharedPreferences).
  const [access, refresh, accountId] = await Promise.all([
    secureGet(SecureKeys.accessToken),
    secureGet(SecureKeys.refreshToken),
    secureGet(SecureKeys.accountId),
  ]);
  if (access && refresh && accountId) {
    dispatch(
      authActions.tokensSet({
        accessToken: access,
        refreshToken: refresh,
        accessTokenExpiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        refreshTokenExpiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        sessionId: '',
        accountId,
      }),
    );
  } else {
    dispatch(authActions.bootstrapResolved({ authenticated: false }));
  }
};

export const signin =
  (email: string, password: string) =>
  async (dispatch: AppDispatch): Promise<void> => {
    const body: SigninRequest = {
      email,
      password,
      deviceId: await getDeviceId(),
      deviceLabel: getDeviceLabel(),
      devicePlatform: getDevicePlatform(),
    };
    const res = await apiClient().post<SigninResponse, SigninRequest>(
      '/auth/signin',
      body,
    );
    await persistTokens(res.tokens);
    dispatch(authActions.tokensSet(res.tokens));
  };

export const signup =
  (email: string, password: string, displayName: string) =>
  async (dispatch: AppDispatch): Promise<void> => {
    const body: SignupRequest = {
      email,
      password,
      displayName,
      deviceId: await getDeviceId(),
      deviceLabel: getDeviceLabel(),
      devicePlatform: getDevicePlatform(),
    };
    const res = await apiClient().post<SignupResponse, SignupRequest>(
      '/auth/signup',
      body,
    );
    await persistTokens(res.tokens);
    dispatch(authActions.tokensSet(res.tokens));
  };

export const signout = () => async (dispatch: AppDispatch): Promise<void> => {
  try {
    await apiClient().post('/auth/signout');
  } catch (e) {
    logger.warn('signout.error', { error: String(e) });
  }
  await clearAllSecrets();
  await secureDelete(SecureKeys.deviceId);
  dispatch(authActions.signedOut());
};

export const refreshAccess =
  (getRefreshToken: () => string | null, dispatch: AppDispatch) =>
  async (): Promise<string | null> => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      dispatch(authActions.refreshing());
      const body: RefreshRequest = {
        refreshToken,
        deviceId: await getDeviceId(),
      };
      const res = await apiClient().post<TokenPair, RefreshRequest>(
        '/auth/refresh',
        body,
      );
      await persistTokens(res);
      dispatch(authActions.tokensSet(res));
      return res.accessToken;
    } catch (e) {
      logger.warn('refresh.failed', { error: String(e) });
      await clearAllSecrets();
      dispatch(authActions.signedOut());
      return null;
    }
  };
