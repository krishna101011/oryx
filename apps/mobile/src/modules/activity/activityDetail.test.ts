/**
 * Activity row → intake item detail resolution.
 *
 * The dispatcher stores the raw event payload on each activity_inbox row;
 * intake.item.received payloads carry intakeItemId (camelCase — the exact key
 * the backend's enqueue_event writes in services/intake/service.py). These
 * tests pin that an intake-backed row resolves to its item id and that every
 * other row shape resolves to null (press = mark-read only, no navigation).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { intakeItemIdOf } from './activityDetail';

test('an intake.item.received row resolves to its intakeItemId', () => {
  // The real payload shape enqueue_event writes (service.py step 7).
  const row = {
    data: {
      intakeItemId: 'a3a5f3a0-0000-4000-8000-000000000001',
      workspaceId: 'ws-1',
      intakeSourceId: 'src-1',
      providerName: 'rss',
      receivedAt: '2026-07-11T14:30:00+00:00',
      fingerprint: 'fp',
      externalId: 'x-1',
    },
  };
  assert.equal(intakeItemIdOf(row), 'a3a5f3a0-0000-4000-8000-000000000001');
});

test('a security event row (no intake payload) resolves to null — press stays mark-read only', () => {
  assert.equal(
    intakeItemIdOf({ data: { sessionId: 's-1', ip: '10.0.0.1' } }),
    null,
  );
});

test('an empty or missing data payload resolves to null, never throws', () => {
  assert.equal(intakeItemIdOf({ data: {} }), null);
  // Defensive: pydantic defaults data to {}, but a malformed row must not crash the feed.
  assert.equal(intakeItemIdOf({ data: undefined as never }), null);
});

test('a malformed intakeItemId (non-string or empty) resolves to null', () => {
  assert.equal(intakeItemIdOf({ data: { intakeItemId: 42 } }), null);
  assert.equal(intakeItemIdOf({ data: { intakeItemId: '' } }), null);
  assert.equal(intakeItemIdOf({ data: { intakeItemId: null } }), null);
});
