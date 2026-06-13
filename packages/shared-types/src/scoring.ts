/**
 * Phase 4 Wave C — the scoring contract shared by FE and BE.
 *
 * Two things live here because both sides must agree on them exactly:
 *   1. CURRENT_SCORING_VERSION — bumped when the composite formula changes;
 *      stamped onto every verification_run so historical scores stay
 *      interpretable (ADR-032).
 *   2. EPISTEMIC_CEILINGS — the permanent upper bound on confidence for each
 *      epistemic type (ADR-036). A claim can never out-score its own type.
 *
 * The confidence BANDS below are presentational only — a coarse bucket for
 * the UI. They are NOT part of the scoring math and must never feed back
 * into a score.
 */
import type { EpistemicType } from './claims';

export const CURRENT_SCORING_VERSION = 1;

/**
 * Permanent confidence ceilings by epistemic type. `null` means "unscorable"
 * (unclassified): no ceiling exists, so no confidence score is produced.
 */
export const EPISTEMIC_CEILINGS: Record<EpistemicType, number | null> = {
  fact: 1.0,
  claim: 0.85,
  speculation: 0.6,
  rumor: 0.4,
  opinion: 0.3,
  unclassified: null,
};

export type ConfidenceBand = 'high' | 'moderate' | 'low' | 'minimal' | 'unscored';

/** Inclusive lower bounds for each band, highest first. */
export const CONFIDENCE_BAND_THRESHOLDS: ReadonlyArray<[ConfidenceBand, number]> = [
  ['high', 0.75],
  ['moderate', 0.5],
  ['low', 0.25],
  ['minimal', 0.0],
];

/** Bucket a confidence score for display. `null` (unscored) → 'unscored'. */
export function confidenceBand(score: number | null): ConfidenceBand {
  if (score === null) return 'unscored';
  for (const [band, floor] of CONFIDENCE_BAND_THRESHOLDS) {
    if (score >= floor) return band;
  }
  return 'minimal';
}
