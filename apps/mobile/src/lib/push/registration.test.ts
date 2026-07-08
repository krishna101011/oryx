/**
 * Phase 6 Wave C — push registration decision logic.
 *
 * Runs on node's built-in test runner via tsx (`pnpm test`); registration.ts
 * is deliberately pure TS with injected effects, so the full decision tree —
 * including the mandatory scenarios (token POSTed; permission denial handled
 * without crash; the Expo Go / web guard never registers a token) — is
 * provable without the jest-expo infra the app does not have.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { AlertDevice, RegisterAlertDeviceRequest } from '@oryx/shared-types';
import {
  type PushEffects,
  type PushEnvironment,
  type PushPermissionStatus,
  type StoredRegistration,
  syncPushRegistration,
  unregisterPush,
} from './registration';

interface FakeOptions {
  status?: PushPermissionStatus;
  canAskAgain?: boolean;
  requestResult?: PushPermissionStatus;
  token?: string | Error;
  stored?: StoredRegistration | null;
  registerError?: Error;
}

function fakes(options: FakeOptions = {}) {
  const calls = {
    requestPermission: 0,
    getRawDeviceToken: 0,
    registered: [] as RegisterAlertDeviceRequest[],
    disabled: [] as string[],
    written: [] as (StoredRegistration | null)[],
    logs: [] as string[],
  };
  let stored: StoredRegistration | null = options.stored ?? null;
  const effects: PushEffects = {
    async getPermissions() {
      return {
        status: options.status ?? 'granted',
        canAskAgain: options.canAskAgain ?? true,
      };
    },
    async requestPermission() {
      calls.requestPermission += 1;
      return options.requestResult ?? 'granted';
    },
    async getRawDeviceToken() {
      calls.getRawDeviceToken += 1;
      const token = options.token ?? 'raw-fcm-token-1';
      if (token instanceof Error) throw token;
      return token;
    },
    async registerDevice(body) {
      if (options.registerError) throw options.registerError;
      calls.registered.push(body);
      return {
        id: `rec-${calls.registered.length}`,
        platform: body.platform,
        appVersion: body.appVersion ?? null,
        lastSeenAt: '2026-07-07T00:00:00Z',
      } as AlertDevice;
    },
    async disableDevice(id) {
      calls.disabled.push(id);
    },
    async readStored() {
      return stored;
    },
    async writeStored(value) {
      calls.written.push(value);
      stored = value;
    },
    log(event) {
      calls.logs.push(event);
    },
  };
  return { effects, calls, stored: () => stored };
}

const android: PushEnvironment = {
  platform: 'android',
  isExpoGo: false,
  appVersion: '0.1.0',
};

// --- Mandatory scenario 1 (client half): token POSTed with the exact shape ---

test('grants permission, POSTs the raw token in the endpoint payload shape, stores the record', async () => {
  const { effects, calls, stored } = fakes({ status: 'undetermined' });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'registered');
  assert.equal(calls.requestPermission, 1);
  // EXACTLY RegisterAlertDeviceRequest: platform + pushToken + appVersion.
  assert.deepEqual(calls.registered, [
    { platform: 'android', pushToken: 'raw-fcm-token-1', appVersion: '0.1.0' },
  ]);
  assert.deepEqual(stored(), {
    token: 'raw-fcm-token-1',
    deviceRecordId: 'rec-1',
  });
});

// --- Mandatory scenario 2: permission denial — no crash, no nagging ---

test('permission denied at the prompt: no crash, nothing registered', async () => {
  const { effects, calls } = fakes({
    status: 'undetermined',
    requestResult: 'denied',
  });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'skipped-permission-denied');
  assert.deepEqual(calls.registered, []);
  assert.equal(calls.getRawDeviceToken, 0);
});

test('previously denied permission is never re-prompted', async () => {
  const { effects, calls } = fakes({ status: 'denied', canAskAgain: false });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'skipped-permission-denied');
  assert.equal(calls.requestPermission, 0); // no repeated nagging
  assert.deepEqual(calls.registered, []);
});

// --- Mandatory guard test: Expo Go / web behave safely ---

test('Expo Go environment: hard skip — no permission prompt, no token, nothing registered', async () => {
  const { effects, calls } = fakes();
  const expoGo: PushEnvironment = {
    platform: 'ios',
    isExpoGo: true,
    appVersion: '0.1.0',
  };

  const outcome = await syncPushRegistration(expoGo, effects);

  // A raw token fetched inside Expo Go would belong to Expo Go's own app
  // identity — unusable by FCMProvider/APNsProvider — so nothing may run.
  assert.equal(outcome, 'skipped-expo-go');
  assert.equal(calls.requestPermission, 0);
  assert.equal(calls.getRawDeviceToken, 0);
  assert.deepEqual(calls.registered, []);
  assert.deepEqual(calls.written, []);
});

test('web environment: hard skip — browser push is out of scope this wave', async () => {
  const { effects, calls } = fakes();
  const web: PushEnvironment = { platform: 'web', isExpoGo: false, appVersion: null };

  const outcome = await syncPushRegistration(web, effects);

  assert.equal(outcome, 'skipped-web');
  assert.equal(calls.getRawDeviceToken, 0);
  assert.deepEqual(calls.registered, []);
});

// --- Token refresh ---

test('rotated token re-registers, disables the stale record, updates storage', async () => {
  const { effects, calls, stored } = fakes({
    token: 'raw-fcm-token-2',
    stored: { token: 'raw-fcm-token-1', deviceRecordId: 'rec-old' },
  });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'refreshed');
  assert.equal(calls.registered[0]?.pushToken, 'raw-fcm-token-2');
  assert.deepEqual(calls.disabled, ['rec-old']);
  assert.deepEqual(stored(), {
    token: 'raw-fcm-token-2',
    deviceRecordId: 'rec-1',
  });
});

test('unchanged token makes no network call at all', async () => {
  const { effects, calls } = fakes({
    stored: { token: 'raw-fcm-token-1', deviceRecordId: 'rec-old' },
  });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'already-registered');
  assert.deepEqual(calls.registered, []);
  assert.deepEqual(calls.disabled, []);
});

// --- Permission revoked after a registration existed ---

test('revoked permission disables the existing registration', async () => {
  const { effects, calls, stored } = fakes({
    status: 'denied',
    canAskAgain: false,
    stored: { token: 'raw-fcm-token-1', deviceRecordId: 'rec-old' },
  });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'unregistered');
  assert.deepEqual(calls.disabled, ['rec-old']);
  assert.equal(stored(), null);
});

// --- Degradation: never throws ---

test('token fetch failure degrades to a skip, not a crash', async () => {
  const { effects, calls } = fakes({ token: new Error('no native module') });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'skipped-token-unavailable');
  assert.deepEqual(calls.registered, []);
});

test('registration API failure degrades to failed, not a crash', async () => {
  const { effects, calls } = fakes({ registerError: new Error('HTTP 500') });

  const outcome = await syncPushRegistration(android, effects);

  assert.equal(outcome, 'failed');
  assert.deepEqual(calls.written, []); // nothing recorded for a failed POST
  assert.ok(calls.logs.includes('push.sync_failed'));
});

// --- Sign-out path ---

test('unregisterPush disables the stored record and clears state', async () => {
  const { effects, calls, stored } = fakes({
    stored: { token: 'raw-fcm-token-1', deviceRecordId: 'rec-old' },
  });

  await unregisterPush(effects);

  assert.deepEqual(calls.disabled, ['rec-old']);
  assert.equal(stored(), null);
});

test('unregisterPush is a silent no-op with nothing stored, and survives a failing DELETE', async () => {
  const clean = fakes();
  await unregisterPush(clean.effects);
  assert.deepEqual(clean.calls.disabled, []);

  const failing = fakes({
    stored: { token: 't', deviceRecordId: 'rec-x' },
  });
  failing.effects.disableDevice = async () => {
    throw new Error('network down');
  };
  await unregisterPush(failing.effects); // must not throw
  assert.equal(failing.stored(), null); // local state still cleared
});
