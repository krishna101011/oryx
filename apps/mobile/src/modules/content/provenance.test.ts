/**
 * Transparency — provenance presenter for the "show your work" view.
 *
 * Feeds presentProvenance the exact shape GET
 * /v1/publications/{id}/provenance emits (snapshot entries, strongest first)
 * and asserts the display rows: labels, restrained tones, preserved order.
 * The immutability of the underlying snapshot is proven server-side in
 * apps/backend/tests/integration/test_publication_provenance.py — this file
 * proves the client renders snapshot values verbatim (no recomputation).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { PublicationCitationSnapshot } from '@oryx/shared-types';
import {
  presentProvenance,
  provenanceSummary,
  snapshotNote,
} from './provenance';

const entry = (
  over: Partial<PublicationCitationSnapshot> = {},
): PublicationCitationSnapshot => ({
  intelligenceObjectId: 'e0000000-0000-0000-0000-000000000001',
  headline: 'Acme raised $5B',
  epistemicType: 'fact',
  confidenceTier: 'high',
  confidenceScore: 0.9,
  scoringVersion: 1,
  snapshottedAt: '2026-07-09T10:00:00Z',
  ...over,
});

test('rows carry labels from the snapshot tier and epistemic type', () => {
  const rows = presentProvenance([
    entry(),
    entry({
      intelligenceObjectId: 'e0000000-0000-0000-0000-000000000002',
      headline: 'Rival denies merger talk',
      epistemicType: 'rumor',
      confidenceTier: 'low',
      confidenceScore: 0.3,
    }),
  ]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0]?.headline, 'Acme raised $5B');
  assert.equal(rows[0]?.tierLabel, 'High confidence');
  assert.equal(rows[0]?.epistemicLabel, 'Fact');
  assert.equal(rows[1]?.tierLabel, 'Low confidence');
  assert.equal(rows[1]?.epistemicLabel, 'Rumor');
});

test('only the high tier carries the accent tone; the rest stay grey', () => {
  const tones = presentProvenance([
    entry({ confidenceTier: 'high' }),
    entry({ confidenceTier: 'moderate' }),
    entry({ confidenceTier: 'low' }),
    entry({ confidenceTier: 'minimal' }),
    entry({ confidenceTier: 'unscored', confidenceScore: null }),
  ]).map((r) => r.tone);
  assert.deepEqual(tones, [
    'brand',
    'secondary',
    'tertiary',
    'tertiary',
    'tertiary',
  ]);
});

test('server order is preserved verbatim (no client re-sort)', () => {
  const rows = presentProvenance([
    entry({ intelligenceObjectId: 'b', confidenceScore: 0.2, confidenceTier: 'low' }),
    entry({ intelligenceObjectId: 'a', confidenceScore: 0.9, confidenceTier: 'high' }),
  ]);
  assert.deepEqual(
    rows.map((r) => r.key),
    ['b', 'a'],
  );
});

test('summary copy pluralizes correctly', () => {
  assert.equal(provenanceSummary(0), 'No cited sources');
  assert.equal(provenanceSummary(1), '1 verified source');
  assert.equal(provenanceSummary(3), '3 verified sources');
});

test('snapshot note anchors to the publish moment and survives bad input', () => {
  assert.match(snapshotNote([entry()]), /^As verified at publish time · /);
  assert.equal(snapshotNote([]), 'As verified at publish time');
  assert.equal(
    snapshotNote([entry({ snapshottedAt: 'not-a-date' })]),
    'As verified at publish time',
  );
});
