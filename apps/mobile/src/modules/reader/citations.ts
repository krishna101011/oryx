/**
 * Public Reader Rev 1 — citation presenter.
 *
 * GET /public/pages/{slug} returns a raw confidenceScore per citation (no
 * confidenceTier — that bucketing is applied server-side elsewhere, e.g.
 * services/publishing/citations.py's _confidence_tier, but this endpoint's
 * allow-list response never ran a citation through it). Scoring.confidenceBand
 * is the SAME canonical bucketing (packages/shared-types/src/scoring.ts,
 * identical thresholds to _confidence_tier) — reusing it here, rather than
 * re-deriving buckets, keeps this screen's tiers in lockstep with every other
 * confidence display in the app. Labels/tones are the same tables the
 * authenticated "show your work" provenance view uses (modules/content/
 * provenance.ts) — one copy/tone source, not a second scheme.
 */
import { Scoring } from '@oryx/shared-types';
import { EPISTEMIC_LABEL, type ProvenanceTone, TIER_LABEL, TIER_TONE } from '../content/provenance';
import type { PublicPageCitation } from './api/publicPages';

export interface PublicCitationRow {
  key: string;
  headline: string;
  tierLabel: string;
  tone: ProvenanceTone;
  epistemicLabel: string;
}

export function presentPublicCitations(
  citations: PublicPageCitation[],
): PublicCitationRow[] {
  return citations.map((c, i) => {
    const tier = Scoring.confidenceBand(c.confidenceScore);
    return {
      key: `${i}-${c.snapshottedAt}`,
      headline: c.headline,
      tierLabel: TIER_LABEL[tier] ?? TIER_LABEL.unscored,
      tone: TIER_TONE[tier] ?? 'tertiary',
      epistemicLabel: EPISTEMIC_LABEL[c.epistemicType] ?? EPISTEMIC_LABEL.unclassified,
    };
  });
}
