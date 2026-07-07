/**
 * Phase 6 Wave B — plain-language label mapping.
 *
 * Runs on node's built-in test runner via tsx (`pnpm test`); these modules
 * are deliberately pure TS (no react-native imports) so they are testable
 * without the jest-expo infra the app does not yet have.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  ALERT_CATEGORIES,
  CATEGORY_COPY,
  FREQUENCY_COPY,
  categoryLabel,
  humanize,
} from './alertCategories';

test('every real alert category has human copy distinct from the raw enum', () => {
  assert.deepEqual(
    [...ALERT_CATEGORIES],
    ['security', 'system', 'verification', 'publishing'],
  );
  for (const category of ALERT_CATEGORIES) {
    const { label, description } = CATEGORY_COPY[category];
    assert.notEqual(label, category); // never the raw enum string
    assert.match(label, /^[A-Z]/); // reads as copy, not an identifier
    assert.ok(description.length > 0);
  }
});

test('categoryLabel maps known categories and never echoes a raw enum', () => {
  assert.equal(categoryLabel('verification'), 'Verification alerts');
  assert.equal(categoryLabel('publishing'), 'Publishing alerts');
  assert.equal(categoryLabel('security'), 'Security alerts');
  assert.equal(categoryLabel('system'), 'System updates');
});

test('categoryLabel humanizes unknown values instead of rendering them raw', () => {
  assert.equal(categoryLabel('daily_digest'), 'Daily digest');
  assert.equal(categoryLabel('some_future_type'), 'Some future type');
});

test('every frequency has human copy including digest send times', () => {
  assert.equal(FREQUENCY_COPY.off.label, 'Off');
  assert.equal(FREQUENCY_COPY.instant.label, 'Instant');
  assert.equal(FREQUENCY_COPY.daily.label, 'Daily digest');
  assert.equal(FREQUENCY_COPY.weekly.label, 'Weekly digest');
  assert.match(FREQUENCY_COPY.daily.description, /8:00/);
  assert.match(FREQUENCY_COPY.weekly.description, /Monday/);
});

test('humanize converts event-type dot/underscore strings to sentence copy', () => {
  assert.equal(humanize('content.publish.failed'), 'Content publish failed');
  assert.equal(humanize('intake.item.received'), 'Intake item received');
});
