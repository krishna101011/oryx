/**
 * Device identification.
 * - deviceId is a persistent random uuid bound to this install (SecureStore).
 * - deviceLabel / devicePlatform come from RN Platform info.
 */
import { Platform } from 'react-native';
import { SecureKeys, secureGet, secureSet } from './secure-store';
import type { DevicePlatform } from '@anant/shared-types';

function randomUuid(): string {
  // Prefer Web Crypto if available; otherwise a v4-ish fallback.
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  const r = () => Math.floor(Math.random() * 0x10000).toString(16).padStart(4, '0');
  return `${r()}${r()}-${r()}-${r()}-${r()}-${r()}${r()}${r()}`;
}

let cachedDeviceId: string | null = null;

export async function getDeviceId(): Promise<string> {
  if (cachedDeviceId) return cachedDeviceId;
  const existing = await secureGet(SecureKeys.deviceId);
  if (existing) {
    cachedDeviceId = existing;
    return existing;
  }
  const fresh = randomUuid();
  await secureSet(SecureKeys.deviceId, fresh);
  cachedDeviceId = fresh;
  return fresh;
}

export function getDevicePlatform(): DevicePlatform {
  if (Platform.OS === 'ios') return 'ios';
  if (Platform.OS === 'android') return 'android';
  return 'web';
}

export function getDeviceLabel(): string {
  // Phase 2: a humane label. Phase 6+ can pull a richer model name.
  const platform = getDevicePlatform();
  return platform === 'ios' ? 'iPhone' : platform === 'android' ? 'Android' : 'Web';
}
