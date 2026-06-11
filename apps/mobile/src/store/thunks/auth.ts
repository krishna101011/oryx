import type {
  RefreshRequest,
  SigninRequest,
  SignupRequest,
  TokenPair,
  SigninResponse,
  SignupResponse,
} from '@anant/shared-types';
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
