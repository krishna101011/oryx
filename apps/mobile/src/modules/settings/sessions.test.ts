import assert from 'node:assert/strict';
import { test } from 'node:test';
import { deviceCountSub } from './sessions';

test('deviceCountSub stays silent while loading, states a real zero plainly, and pluralizes', () => {
  assert.equal(deviceCountSub(undefined), undefined);
  assert.equal(deviceCountSub([]), '0 DEVICES');
  const s = {
    id: 'a',
    deviceLabel: 'MacBook Pro',
    devicePlatform: 'web' as const,
    current: true,
    lastUsedAt: '2026-07-20T00:00:00Z',
    createdAt: '2026-07-20T00:00:00Z',
    expiresAt: '2026-08-20T00:00:00Z',
  };
  assert.equal(deviceCountSub([s]), '1 DEVICE');
  assert.equal(deviceCountSub([s, { ...s, id: 'b', current: false }]), '2 DEVICES');
});
