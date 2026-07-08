/**
 * SecureStore wrapper — typed, prefixed keys, single-source for secret persistence.
 * Uses expo-secure-store (Keychain on iOS, EncryptedSharedPreferences on Android).
 * Web build (Expo dev) falls back to in-memory; we never ship web with real secrets.
 */
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const PREFIX = 'oryx.';
const memoryFallback = new Map<string, string>();

const isAvailable = Platform.OS === 'ios' || Platform.OS === 'android';

export const SecureKeys = {
  accessToken: 'auth.access_token',
  refreshToken: 'auth.refresh_token',
  accountId: 'auth.account_id',
  deviceId: 'device.id',
  // Phase 6 Wave C: JSON {token, deviceRecordId} for the registered push
  // token (lib/push/registration.ts StoredRegistration).
  pushRegistration: 'push.registration',
} as const;

export type SecureKey = (typeof SecureKeys)[keyof typeof SecureKeys];

export async function secureGet(key: SecureKey): Promise<string | null> {
  const full = PREFIX + key;
  if (!isAvailable) return memoryFallback.get(full) ?? null;
  return SecureStore.getItemAsync(full);
}

export async function secureSet(key: SecureKey, value: string): Promise<void> {
  const full = PREFIX + key;
  if (!isAvailable) {
    memoryFallback.set(full, value);
    return;
  }
  await SecureStore.setItemAsync(full, value);
}

export async function secureDelete(key: SecureKey): Promise<void> {
  const full = PREFIX + key;
  if (!isAvailable) {
    memoryFallback.delete(full);
    return;
  }
  await SecureStore.deleteItemAsync(full);
}

export async function clearAllSecrets(): Promise<void> {
  await Promise.all(
    Object.values(SecureKeys).map((k) => secureDelete(k as SecureKey)),
  );
}
