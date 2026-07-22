/**
 * Source-governance tier derivation (2026-07-22 wave).
 *
 * Boundaries are calibrated against real data (see sourceTier.ts's own
 * doc comment for the full recon): MIN_RATED_CLAIMS=5 (533/570 real
 * source_credibility_records sit at 0 claims, 35 more at 1-4 — only 2 had a
 * real sample), PRIMARY_THRESHOLD=0.90 (the real curated editorial_confidence
 * ceiling: Bloomberg 92, Reuters/FT 90), REVIEW_THRESHOLD=0.5 (the EMA in
 * verification/credibility.py never starts below 0.5 from any real prior,
 * so sub-0.5 is always real accumulated contested evidence).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  MIN_RATED_CLAIMS,
  PRIMARY_THRESHOLD,
  REVIEW_THRESHOLD,
  deriveSourceTier,
  formatSourceTier,
  needsReviewRecommendation,
} from './sourceTier';

test('the real calibrated constants are what the recon derived, not placeholders', () => {
  assert.equal(MIN_RATED_CLAIMS, 5);
  assert.equal(PRIMARY_THRESHOLD, 0.9);
  assert.equal(REVIEW_THRESHOLD, 0.5);
});

// -------------------- the minimum-sample-size gate --------------------

test('below MIN_RATED_CLAIMS is not_rated regardless of accuracy_rate', () => {
  assert.deepEqual(deriveSourceTier(0.97, 0), { kind: 'not_rated' });
  assert.deepEqual(deriveSourceTier(0.97, 1), { kind: 'not_rated' });
  assert.deepEqual(deriveSourceTier(0.97, MIN_RATED_CLAIMS - 1), { kind: 'not_rated' });
  // Even a terrible accuracy_rate on thin history is not_rated, not needs_review —
  // one bad outcome is not the same real signal as a sustained pattern.
  assert.deepEqual(deriveSourceTier(0.1, 2), { kind: 'not_rated' });
});

test('MIN_RATED_CLAIMS itself is enough to receive a real tier', () => {
  const tier = deriveSourceTier(0.95, MIN_RATED_CLAIMS);
  assert.deepEqual(tier, { kind: 'rated', tier: 'primary' });
});

// -------------------- PRIMARY / TRUSTED / NEEDS_REVIEW boundaries --------------------

test('PRIMARY_THRESHOLD is an inclusive floor for primary', () => {
  assert.deepEqual(deriveSourceTier(PRIMARY_THRESHOLD, 10), {
    kind: 'rated', tier: 'primary',
  });
  assert.deepEqual(deriveSourceTier(PRIMARY_THRESHOLD - 0.001, 10), {
    kind: 'rated', tier: 'trusted',
  });
});

test('REVIEW_THRESHOLD is an exclusive floor for trusted (below it is needs_review)', () => {
  assert.deepEqual(deriveSourceTier(REVIEW_THRESHOLD, 10), {
    kind: 'rated', tier: 'trusted',
  });
  assert.deepEqual(deriveSourceTier(REVIEW_THRESHOLD - 0.001, 10), {
    kind: 'rated', tier: 'needs_review',
  });
});

test('the real observed live-workspace values (CoinTelegraph 0.968, The Block 0.939) both land PRIMARY', () => {
  assert.deepEqual(deriveSourceTier(0.9676945905538666, 122), {
    kind: 'rated', tier: 'primary',
  });
  assert.deepEqual(deriveSourceTier(0.9392116727047154, 102), {
    kind: 'rated', tier: 'primary',
  });
});

test('the neutral bootstrap prior (0.5) with a real sample size is trusted, not needs_review', () => {
  // 0.5 is the DEFAULT for "no verification signal yet" (ADR-031) — once a
  // source clears the sample gate while still sitting exactly at neutral,
  // it must not read as a red flag.
  assert.deepEqual(deriveSourceTier(0.5, MIN_RATED_CLAIMS), {
    kind: 'rated', tier: 'trusted',
  });
});

// -------------------- formatting: reuses the dormant-state convention --------------------

test('not_rated renders with the EXACT dormant-state copy/tone convention', () => {
  assert.deepEqual(formatSourceTier({ kind: 'not_rated' }), {
    text: 'not yet rated',
    tone: 'neutral',
  });
});

test('primary/trusted/needs_review render with the expected tone', () => {
  assert.deepEqual(formatSourceTier({ kind: 'rated', tier: 'primary' }), {
    text: 'PRIMARY', tone: 'positive',
  });
  assert.deepEqual(formatSourceTier({ kind: 'rated', tier: 'trusted' }), {
    text: 'TRUSTED', tone: 'neutral',
  });
  assert.deepEqual(formatSourceTier({ kind: 'rated', tier: 'needs_review' }), {
    text: 'NEEDS REVIEW', tone: 'danger',
  });
});

// -------------------- review recommendation: human-confirmable, never auto-acting --------------------

test('needsReviewRecommendation fires only for an ENABLED source below REVIEW_THRESHOLD with a real sample', () => {
  const bad = { accuracyRate: 0.3, totalClaimCount: 20 };
  assert.equal(needsReviewRecommendation(bad, true), true);
});

test('needsReviewRecommendation is false for an already-disabled source, however bad the accuracy', () => {
  // MANDATORY: never a signal to auto-disable — and there is nothing to
  // recommend disabling twice. A disabled source shows no flag at all.
  const terrible = { accuracyRate: 0.05, totalClaimCount: 500 };
  assert.equal(needsReviewRecommendation(terrible, false), false);
});

test('needsReviewRecommendation is false below the sample gate, however bad the accuracy', () => {
  const thin = { accuracyRate: 0.1, totalClaimCount: 2 };
  assert.equal(needsReviewRecommendation(thin, true), false);
});

test('needsReviewRecommendation is false for primary and trusted sources', () => {
  assert.equal(needsReviewRecommendation({ accuracyRate: 0.95, totalClaimCount: 50 }, true), false);
  assert.equal(needsReviewRecommendation({ accuracyRate: 0.7, totalClaimCount: 50 }, true), false);
});

test('needsReviewRecommendation never mutates its input (pure signal, no side effect)', () => {
  const input = { accuracyRate: 0.2, totalClaimCount: 30 };
  const snapshot = { ...input };
  needsReviewRecommendation(input, true);
  assert.deepEqual(input, snapshot);
});
