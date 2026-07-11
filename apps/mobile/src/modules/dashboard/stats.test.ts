/**
 * Command Center stats card — the SOURCES stat presenter.
 *
 * The stat was a hardcoded "0" from Phase 1 until 2026-07-11; it now renders
 * sourcesStatValue(useIntakeStatus().data). These tests pin the presenter's
 * whole contract; the backend half (a seeded source really counts in
 * GET /v1/intake/status) is test_intake_status_api.py.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { IntakeStatusSummary } from '@oryx/shared-types';
import { sourcesStatValue } from './stats';

const seeded: IntakeStatusSummary = {
  total: 3,
  byHealth: { healthy: 2, degraded: 1, auth_required: 0, disabled: 0 },
};

test('Command Center SOURCES stat shows the real seeded source count, not zero', () => {
  assert.equal(sourcesStatValue(seeded), '3');
});

test('SOURCES stat shows an em dash while loading — never a fake zero', () => {
  assert.equal(sourcesStatValue(undefined), '—');
});

test('a genuine zero still renders as 0, not the loading dash', () => {
  assert.equal(
    sourcesStatValue({ total: 0, byHealth: { healthy: 0, degraded: 0, auth_required: 0, disabled: 0 } }),
    '0',
  );
});
