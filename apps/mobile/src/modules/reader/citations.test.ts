import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { PublicPageCitation } from './api/publicPages';
import { presentPublicCitations } from './citations';

const citation = (over: Partial<PublicPageCitation> = {}): PublicPageCitation => ({
  headline: 'Acme raised $5B',
  epistemicType: 'fact',
  confidenceScore: 0.9,
  scoringVersion: 1,
  snapshottedAt: '2026-07-09T10:00:00Z',
  ...over,
});

test('derives the same tier/tone/label the authenticated provenance view uses, from a raw score', () => {
  const rows = presentPublicCitations([
    citation({ confidenceScore: 0.9 }),
    citation({ confidenceScore: 0.3, epistemicType: 'rumor', headline: 'Rival denies merger talk' }),
  ]);
  assert.equal(rows[0]?.tierLabel, 'High confidence');
  assert.equal(rows[0]?.tone, 'brand');
  assert.equal(rows[0]?.epistemicLabel, 'Fact');
  assert.equal(rows[1]?.tierLabel, 'Low confidence');
  assert.equal(rows[1]?.tone, 'tertiary');
  assert.equal(rows[1]?.epistemicLabel, 'Rumor');
});

test('a null confidenceScore buckets to unscored, matching Scoring.confidenceBand', () => {
  const rows = presentPublicCitations([citation({ confidenceScore: null })]);
  assert.equal(rows[0]?.tierLabel, 'Unscored');
  assert.equal(rows[0]?.tone, 'tertiary');
});

test('server order is preserved verbatim (no client re-sort)', () => {
  const rows = presentPublicCitations([
    citation({ headline: 'B', confidenceScore: 0.2 }),
    citation({ headline: 'A', confidenceScore: 0.9 }),
  ]);
  assert.deepEqual(rows.map((r) => r.headline), ['B', 'A']);
});

test('an empty citations list produces an empty row list', () => {
  assert.deepEqual(presentPublicCitations([]), []);
});
