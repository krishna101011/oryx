/**
 * Phase 6 Wave B — Automation Hub Log-tab presenter.
 *
 * Feeds toFeedRows realistic GET /v1/automation-log payloads (the exact
 * shapes the backend's _dispatch_entry/_digest_entry emit) and asserts the
 * screen rows: human copy, correct tones, newest-first order.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { Automation } from '@oryx/shared-types';
import { toFeedRow, toFeedRows } from './feed';

const dispatchEntry = (
  over: Partial<Automation.AutomationLogEntry> = {},
): Automation.AutomationLogEntry => ({
  id: 'a4f7d9e2-0000-0000-0000-000000000001',
  kind: 'dispatch',
  action: 'notification_created',
  eventType: 'content.published',
  category: null,
  frequency: null,
  windowStart: null,
  windowEnd: null,
  activityInboxId: 'b0000000-0000-0000-0000-000000000002',
  createdAt: '2026-07-06T10:00:00Z',
  ...over,
});

const digestEntry = (
  over: Partial<Automation.AutomationLogEntry> = {},
): Automation.AutomationLogEntry => ({
  id: 'c0000000-0000-0000-0000-000000000003',
  kind: 'digest',
  action: 'digest_sent',
  eventType: null,
  category: 'publishing',
  frequency: 'daily',
  windowStart: '2026-07-05T12:00:00Z',
  windowEnd: '2026-07-06T12:00:00Z',
  activityInboxId: null,
  createdAt: '2026-07-06T12:00:00Z',
  ...over,
});

test('a dispatch entry renders human copy, never the raw action or event enum', () => {
  const row = toFeedRow(dispatchEntry());
  assert.equal(row.title, 'Notification delivered');
  assert.equal(row.subtitle, 'Content published');
  assert.equal(row.tone, 'positive');
  assert.ok(!row.title.includes('notification_created'));
  assert.ok(!row.subtitle.includes('content.published'));
});

test('a suppression renders as warn tone with its own copy', () => {
  const row = toFeedRow(dispatchEntry({ action: 'suppressed_by_preference' }));
  assert.equal(row.title, 'Suppressed by your preferences');
  assert.equal(row.tone, 'warn');
  assert.equal(row.icon, 'BellOff');
});

test('a digest entry renders cadence + category label from the real row shape', () => {
  const daily = toFeedRow(digestEntry());
  assert.equal(daily.title, 'Daily digest sent');
  assert.equal(daily.subtitle, 'Publishing alerts');
  assert.equal(daily.icon, 'Layers');

  const weekly = toFeedRow(digestEntry({ frequency: 'weekly', category: 'verification' }));
  assert.equal(weekly.title, 'Weekly digest sent');
  assert.equal(weekly.subtitle, 'Verification alerts');
});

test('push_failed maps to danger tone (Wave C vocabulary, typed now)', () => {
  const row = toFeedRow(dispatchEntry({ action: 'push_failed' }));
  assert.equal(row.tone, 'danger');
  assert.equal(row.icon, 'AlertTriangle');
});

test('toFeedRows orders a merged dispatch+digest payload newest first', () => {
  const rows = toFeedRows([
    dispatchEntry({ id: 'old', createdAt: '2026-07-06T10:00:00Z' }),
    digestEntry({ id: 'new', createdAt: '2026-07-06T12:00:00Z' }),
    dispatchEntry({ id: 'mid', createdAt: '2026-07-06T11:00:00Z', action: 'suppressed_by_preference' }),
  ]);
  assert.deepEqual(rows.map((r) => r.id), ['new', 'mid', 'old']);
});
