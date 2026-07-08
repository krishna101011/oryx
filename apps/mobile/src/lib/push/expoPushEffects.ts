/**
 * Expo-bound adapter for the pure registration logic — Phase 6 Wave C.
 *
 * PHASE 0 CAPABILITY NOTE (why getDevicePushTokenAsync, and its limits):
 * expo-notifications ~0.28 (the SDK 51 pair) exposes BOTH
 * getExpoPushTokenAsync() — an ExpoPushToken[...] routed through Expo's relay
 * — and getDevicePushTokenAsync() — the RAW platform token (native APNs
 * device token on iOS, FCM registration token on Android). ORYX's backend
 * providers send directly to Firebase/Apple, so ONLY the raw token is usable
 * here. Raw tokens carry the app's own push identity, which exists only in a
 * development/production build with native push config (Android:
 * google-services.json wired via app.json android.googleServicesFile; iOS:
 * the aps-environment entitlement from a provisioned build). This project is
 * currently Expo Go-configured (no expo-dev-client), so at runtime the
 * registration is guarded OFF in Expo Go and on web — it activates the moment
 * a dev build exists, and can never register a token the providers can't use.
 */
import Constants, { ExecutionEnvironment } from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import type { AlertDevice, RegisterAlertDeviceRequest } from '@oryx/shared-types';
import { apiClient } from '../api/client';
import { logger } from '../logger';
import { SecureKeys, secureDelete, secureGet, secureSet } from '../secure-store';
import type {
  PushEffects,
  PushEnvironment,
  PushPermissionStatus,
  StoredRegistration,
} from './registration';

export function expoPushEnvironment(): PushEnvironment {
  const platform =
    Platform.OS === 'ios' ? 'ios' : Platform.OS === 'android' ? 'android' : 'web';
  return {
    platform,
    isExpoGo:
      Constants.executionEnvironment === ExecutionEnvironment.StoreClient,
    appVersion: Constants.expoConfig?.version ?? null,
  };
}

// expo-modules-core PermissionStatus values ('granted'|'denied'|'undetermined');
// compared as literals because expo-notifications 0.28 does not re-export the
// enum object itself.
function mapStatus(status: string): PushPermissionStatus {
  if (status === 'granted') return 'granted';
  if (status === 'denied') return 'denied';
  return 'undetermined';
}

async function readStored(): Promise<StoredRegistration | null> {
  const raw = await secureGet(SecureKeys.pushRegistration);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredRegistration;
    return parsed.token && parsed.deviceRecordId ? parsed : null;
  } catch {
    return null;
  }
}

export function expoPushEffects(): PushEffects {
  return {
    async getPermissions() {
      const res = await Notifications.getPermissionsAsync();
      return { status: mapStatus(res.status), canAskAgain: res.canAskAgain };
    },
    async requestPermission() {
      const res = await Notifications.requestPermissionsAsync();
      return mapStatus(res.status);
    },
    async getRawDeviceToken() {
      const token = await Notifications.getDevicePushTokenAsync();
      return String(token.data);
    },
    registerDevice(body: RegisterAlertDeviceRequest) {
      return apiClient().post<AlertDevice, RegisterAlertDeviceRequest>(
        '/activity/devices',
        body,
      );
    },
    async disableDevice(deviceRecordId: string) {
      await apiClient().delete(`/activity/devices/${deviceRecordId}`);
    },
    readStored,
    async writeStored(value: StoredRegistration | null) {
      if (value === null) {
        await secureDelete(SecureKeys.pushRegistration);
        return;
      }
      await secureSet(SecureKeys.pushRegistration, JSON.stringify(value));
    },
    log(event: string, data?: Record<string, unknown>) {
      logger.info(event, data);
    },
  };
}

/** Re-sync when the OS rotates the device token while the app is alive. */
export function subscribeToTokenRefresh(onToken: () => void): { remove(): void } {
  const sub = Notifications.addPushTokenListener(() => onToken());
  return { remove: () => sub.remove() };
}
