/**
 * Push-token registration logic — Phase 6 Wave C.
 *
 * Deliberately pure TS with every effect injected (no react-native / expo
 * imports), so the decision logic runs under node's test runner via tsx —
 * the same convention as modules/settings/alertCategories.ts. The expo-bound
 * adapter lives in expoPushEffects.ts; the hook in usePushRegistration.ts.
 *
 * Token format contract: the token registered here MUST be the RAW platform
 * token (expo-notifications getDevicePushTokenAsync — the native APNs device
 * token on iOS, the FCM registration token on Android), because the backend's
 * FCMProvider/APNsProvider send directly to Firebase/Apple, not through
 * Expo's relay. ExpoPushToken[...] values are never used. Raw tokens are only
 * meaningful in a development/production build — in Expo Go they belong to
 * Expo Go's own app identity — so Expo Go and web are hard-skipped below and
 * can never register an unusable token.
 */
import type { AlertDevice, RegisterAlertDeviceRequest } from '@oryx/shared-types';

export type PushPermissionStatus = 'granted' | 'denied' | 'undetermined';

export interface PushEnvironment {
  platform: 'ios' | 'android' | 'web';
  /** Running inside Expo Go (raw tokens there are bound to Expo Go's own
   * Firebase project / bundle id — useless to ORYX's providers). */
  isExpoGo: boolean;
  appVersion: string | null;
}

/** What survives across launches (SecureStore): the token we registered and
 * the alert_devices row id the server returned for it. */
export interface StoredRegistration {
  token: string;
  deviceRecordId: string;
}

export interface PushEffects {
  getPermissions(): Promise<{ status: PushPermissionStatus; canAskAgain: boolean }>;
  requestPermission(): Promise<PushPermissionStatus>;
  getRawDeviceToken(): Promise<string>;
  registerDevice(body: RegisterAlertDeviceRequest): Promise<AlertDevice>;
  disableDevice(deviceRecordId: string): Promise<void>;
  readStored(): Promise<StoredRegistration | null>;
  writeStored(value: StoredRegistration | null): Promise<void>;
  log(event: string, data?: Record<string, unknown>): void;
}

export type SyncOutcome =
  | 'registered' // fresh token POSTed and stored
  | 'refreshed' // token changed: new registration, old record disabled
  | 'already-registered' // stored token still current; no network call
  | 'unregistered' // permission revoked: existing registration disabled
  | 'skipped-web' // browser push is out of scope this wave
  | 'skipped-expo-go' // raw tokens unusable in Expo Go (needs a dev build)
  | 'skipped-permission-denied' // user said no; never re-prompted
  | 'skipped-token-unavailable' // OS would not produce a token
  | 'failed'; // network/API error — logged, never thrown

/**
 * Bring the server's view of this install in line with reality. Never throws.
 *
 * `prompt` controls whether an 'undetermined' permission may trigger the OS
 * dialog — true only from user-meaningful surfaces (the Notification
 * Preferences screen). A 'denied' status NEVER re-prompts, from anywhere.
 */
export async function syncPushRegistration(
  env: PushEnvironment,
  effects: PushEffects,
  options: { prompt?: boolean } = {},
): Promise<SyncOutcome> {
  const prompt = options.prompt ?? true;
  try {
    if (env.platform === 'web') return 'skipped-web';
    if (env.isExpoGo) {
      effects.log('push.skipped_expo_go');
      return 'skipped-expo-go';
    }

    const permissions = await effects.getPermissions();
    let status = permissions.status;
    if (status === 'undetermined' && prompt && permissions.canAskAgain) {
      status = await effects.requestPermission();
    }
    if (status !== 'granted') {
      // Permission absent. If we HAD a registration, it is now stale — the
      // user revoked notifications — so disable it server-side.
      const stored = await effects.readStored();
      if (stored) {
        await effects.disableDevice(stored.deviceRecordId);
        await effects.writeStored(null);
        effects.log('push.unregistered_permission_revoked');
        return 'unregistered';
      }
      return 'skipped-permission-denied';
    }

    let token: string;
    try {
      token = await effects.getRawDeviceToken();
    } catch (e) {
      effects.log('push.token_unavailable', { error: String(e) });
      return 'skipped-token-unavailable';
    }

    const stored = await effects.readStored();
    if (stored && stored.token === token) return 'already-registered';

    const body: RegisterAlertDeviceRequest = {
      platform: env.platform,
      pushToken: token,
      ...(env.appVersion ? { appVersion: env.appVersion } : {}),
    };
    const device = await effects.registerDevice(body);
    if (stored) {
      // Token rotated: the old alert_devices row can never be delivered to.
      await effects.disableDevice(stored.deviceRecordId);
    }
    await effects.writeStored({ token, deviceRecordId: device.id });
    effects.log(stored ? 'push.token_refreshed' : 'push.registered');
    return stored ? 'refreshed' : 'registered';
  } catch (e) {
    effects.log('push.sync_failed', { error: String(e) });
    return 'failed';
  }
}

/**
 * Disable this install's registration (the sign-out path). Must run while the
 * session is still authenticated — the DELETE needs the bearer token. Never
 * throws; a failed disable still clears local state (the server row goes
 * stale, which delivery treats as a failed push, never a crash).
 */
export async function unregisterPush(effects: PushEffects): Promise<void> {
  try {
    const stored = await effects.readStored();
    if (!stored) return;
    try {
      await effects.disableDevice(stored.deviceRecordId);
    } catch (e) {
      effects.log('push.unregister_failed', { error: String(e) });
    }
    await effects.writeStored(null);
    effects.log('push.unregistered_signout');
  } catch (e) {
    effects.log('push.unregister_failed', { error: String(e) });
  }
}
