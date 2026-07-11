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
import { REASON_NOT_RECORDED, toDetailLines, toFeedRow, toFeedRows } from './feed';

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
  channel: 'in_app',
  detail: null,
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
  channel: null,
  detail: null,
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

// ------------------- expanded detail (the row press, 2026-07-12) -------------------

test('a push_failed row expands to the REAL persisted failure reason', () => {
  const lines = toDetailLines(
    dispatchEntry({
      action: 'push_failed',
      channel: 'push',
      eventType: 'intake.item.received',
      detail: 'no_registered_device',
    }),
  );
  assert.deepEqual(lines, [
    { label: 'Channel', value: 'Push' },
    { label: 'Trigger', value: 'Intake item received' },
    { label: 'Reason', value: 'no_registered_device' },
  ]);
});

test('a failed row that predates reason capture says so honestly — never invents a reason', () => {
  const lines = toDetailLines(
    dispatchEntry({ action: 'email_failed', channel: 'email', detail: null }),
  );
  const reason = lines.find((l) => l.label === 'Reason');
  assert.ok(reason, 'failed rows must always carry a Reason line');
  assert.equal(reason.value, REASON_NOT_RECORDED);
});

test('successful and suppressed rows get channel + trigger but NO fabricated reason line', () => {
  for (const action of ['notification_created', 'push_sent', 'suppressed_by_preference'] as const) {
    const lines = toDetailLines(dispatchEntry({ action }));
    assert.equal(lines.some((l) => l.label === 'Reason'), false, `${action} must not carry a Reason`);
    assert.deepEqual(
      lines.map((l) => l.label),
      ['Channel', 'Trigger'],
      `${action} detail lines`,
    );
  }
});

test('a digest row expands to its real window and category, no channel line', () => {
  const lines = toDetailLines(digestEntry());
  assert.deepEqual(lines.map((l) => l.label), ['Window', 'Category']);
  assert.equal(lines[1]!.value, 'Publishing alerts');
  assert.equal(lines.some((l) => l.label === 'Channel'), false);
});

test('every feed row carries its detail lines (the screen renders row.detail on expand)', () => {
  const rows = toFeedRows([
    dispatchEntry({ action: 'push_failed', channel: 'push', detail: 'fcm: unregistered token' }),
    digestEntry(),
  ]);
  for (const row of rows) {
    assert.ok(row.detail.length > 0, `${row.title} must have at least one detail line`);
  }
  assert.equal(
    rows.find((r) => r.title === 'Push failed')!.detail.find((l) => l.label === 'Reason')!.value,
    'fcm: unregistered token',
  );
});
