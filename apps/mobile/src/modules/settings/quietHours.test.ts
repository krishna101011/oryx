/**
 * Phase 6 Wave C — quiet-hours preset mapping.
 *
 * Runs on node's built-in test runner via tsx (`pnpm test`); quietHours.ts is
 * pure TS by design. The evaluation semantics themselves (overnight windows,
 * the empty-window "off" encoding) are backend-owned and covered in
 * apps/backend/tests/unit/test_quiet_hours.py — this file proves the client
 * writes values that round-trip through those semantics.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  QUIET_HOURS_PRESETS,
  buildQuietHours,
  deviceTimeZone,
  presetKeyFor,
} from './quietHours';

test('presets include Off plus real overnight windows in HH:mm form', () => {
  assert.equal(QUIET_HOURS_PRESETS[0]?.key, 'off');
  for (const preset of QUIET_HOURS_PRESETS) {
    assert.match(preset.start, /^\d{2}:\d{2}$/);
    assert.match(preset.end, /^\d{2}:\d{2}$/);
    assert.ok(preset.label.length > 0);
  }
  // Every non-off preset is a genuine overnight window (start > end), the
  // case the backend evaluator must wrap across midnight.
  for (const preset of QUIET_HOURS_PRESETS.slice(1)) {
    assert.ok(preset.start > preset.end, `${preset.key} should wrap midnight`);
  }
});

test('off preset uses the empty-window encoding (start === end)', () => {
  const off = QUIET_HOURS_PRESETS[0]!;
  assert.equal(off.start, off.end);
  // …because the PUT endpoint cannot null out quiet_hours once set; an empty
  // window is the documented "never quiet" value backend-side.
});

test('buildQuietHours stamps the given IANA timezone onto the preset window', () => {
  const night = QUIET_HOURS_PRESETS.find((p) => p.key === 'night')!;
  assert.deepEqual(buildQuietHours(night, 'Asia/Kolkata'), {
    start: '22:00',
    end: '07:00',
    tz: 'Asia/Kolkata',
  });
});

test('presetKeyFor round-trips every preset and recognises the off encodings', () => {
  for (const preset of QUIET_HOURS_PRESETS) {
    const value = buildQuietHours(preset, 'UTC');
    assert.equal(presetKeyFor(value), preset.key);
  }
  assert.equal(presetKeyFor(null), 'off');
  assert.equal(presetKeyFor(undefined), 'off');
  assert.equal(presetKeyFor({ start: '13:37', end: '13:37', tz: 'UTC' }), 'off');
});

test('a hand-set window matching no preset reads as null, never mislabelled', () => {
  assert.equal(presetKeyFor({ start: '01:15', end: '05:45', tz: 'UTC' }), null);
});

test('deviceTimeZone always yields a non-empty zone name', () => {
  const tz = deviceTimeZone();
  assert.ok(typeof tz === 'string' && tz.length > 0);
});
