import type { Verification } from '@oryx/shared-types';

/**
 * Source-governance tier derivation (2026-07-22 wave).
 *
 * Pure view-model logic, no react-native import (tsx --test, same pattern as
 * analytics/presenter.ts). Tiers are DERIVED from the real, already-live
 * source_credibility_records feedback loop (ADR-031) — nothing new is
 * tracked; a source's tier is a pure function of its accuracy_rate and
 * total_claim_count.
 *
 * Calibration (real data, queried against the live workspace + full
 * cross-workspace source_credibility_records table, 2026-07-22 recon —
 * NOT the design-reference mockup's fabricated numbers):
 *
 * - MIN_RATED_CLAIMS = 5: of 570 real records, 533 (93.5%) sit at
 *   total_claim_count = 0 (pure bootstrap, no verification has ever run) and
 *   35 more (6.1%) sit at 1-4 — only 2 records (0.35%) had a real,
 *   substantial sample (102, 122 claims). The cliff between "no/thin signal"
 *   and "real signal" sits well below 5 in the observed data; 5 is a
 *   conservative floor above the thin band, not a guess.
 * - PRIMARY_THRESHOLD = 0.90: the real curated editorial_confidence ceiling
 *   for this catalog's top vendors (Bloomberg 0.92, Reuters 0.90,
 *   Financial Times 0.90) — a source only earns PRIMARY once its EVOLVED,
 *   verification-driven accuracy matches what the project's own editors
 *   consider the top wire-service tier.
 * - REVIEW_THRESHOLD = 0.5: not a guess but a structural fact of the EMA in
 *   verification/credibility.py (ALPHA = 0.1) — every real prior (editorial
 *   or the neutral bootstrap default) starts AT OR ABOVE 0.5, so the ONLY
 *   way a rated source's accuracy_rate falls below 0.5 is sustained
 *   contested outcomes outweighing verified ones. Below 0.5 is therefore
 *   always real accumulated evidence of unreliability, never noise.
 *
 * Only 3 tiers, not the reference mockup's 5 (PRIMARY/TIER-1/TIER-2/TIER-3/
 * QUARANTINE): the real distribution shows exactly one cluster of evolved
 * signal above the priors (0.94-0.97) and one at the neutral floor (0.5) —
 * fabricating 5 precise cutoffs from that shape would be inventing
 * precision the data doesn't support. QUARANTINE is deliberately not a tier
 * at all here — content-trust state (on/review/off) is a separate concept
 * from tier, matching the reference's own separate Tier/State columns, and
 * "off" is never automatic (see needsReviewRecommendation below).
 */

export const MIN_RATED_CLAIMS = 5;
export const PRIMARY_THRESHOLD = 0.9;
export const REVIEW_THRESHOLD = 0.5;

export type SourceTier =
  | { kind: 'not_rated' }
  | { kind: 'rated'; tier: 'primary' | 'trusted' | 'needs_review' };

/**
 * Pure derivation over already-live fields — nothing new is stored.
 * `totalClaimCount` gates the tier the same way a day-count gates a trend:
 * below the real sample floor, there is no honest rate to report at all.
 */
export function deriveSourceTier(
  accuracyRate: number,
  totalClaimCount: number,
): SourceTier {
  if (totalClaimCount < MIN_RATED_CLAIMS) return { kind: 'not_rated' };
  if (accuracyRate < REVIEW_THRESHOLD) return { kind: 'rated', tier: 'needs_review' };
  if (accuracyRate >= PRIMARY_THRESHOLD) return { kind: 'rated', tier: 'primary' };
  return { kind: 'rated', tier: 'trusted' };
}

export interface TierDisplay {
  text: string;
  /** Mirrors the trends dormant-state convention: a real problem is
   * 'danger', a real good result is 'positive', anything else (including
   * "nothing to report yet") is 'neutral' — never invented wording. */
  tone: 'positive' | 'danger' | 'neutral';
}

/** Renderable copy for a tier. 'not yet rated' reuses the EXACT lowercase
 * sentence-fragment convention and neutral tone the trends dormant-state fix
 * established (presenter.ts formatTrend) — not new wording. */
export function formatSourceTier(tier: SourceTier): TierDisplay {
  if (tier.kind === 'not_rated') return { text: 'not yet rated', tone: 'neutral' };
  if (tier.tier === 'primary') return { text: 'PRIMARY', tone: 'positive' };
  if (tier.tier === 'needs_review') return { text: 'NEEDS REVIEW', tone: 'danger' };
  return { text: 'TRUSTED', tone: 'neutral' };
}

/**
 * Whether to surface a human-confirmable review recommendation for a source.
 * Pure and derived — no new persisted state (evaluated against ADR-031's two
 * reserved JSONB seams and found genuinely unnecessary: every input here is
 * already live, so storing a review flag would just be a stale cache of a
 * one-line computation). Never true for an already-disabled source — there
 * is nothing to recommend disabling twice, and this must never auto-disable
 * anything: it only gates whether the UI shows the recommendation banner and
 * lets a human act via the EXISTING enabled toggle.
 */
export function needsReviewRecommendation(
  credibility: Pick<Verification.SourceCredibility, 'accuracyRate' | 'totalClaimCount'>,
  enabled: boolean,
): boolean {
  if (!enabled) return false;
  const tier = deriveSourceTier(credibility.accuracyRate, credibility.totalClaimCount);
  return tier.kind === 'rated' && tier.tier === 'needs_review';
}
