/**
 * Pure presentation logic for the publication provenance ("show your work")
 * view — extracted from PublishHistoryScreen so it runs under the node test
 * runner (frontend tests are pure-logic only, no react-native imports).
 *
 * Everything presented here comes from the publication_citations SNAPSHOT
 * taken when the publication row was created — never a live
 * intelligence-object read — so what a published piece "shows for its work"
 * is immutable even if the object is re-scored later. Intelligence-object
 * level only: the payload carries no claim or evidence data at any depth.
 */
import type { PublicationCitationSnapshot } from '@oryx/shared-types';

type Tier = PublicationCitationSnapshot['confidenceTier'];
type Epistemic = PublicationCitationSnapshot['epistemicType'];

/** Subset of design-system Text colors used by the provenance rows. */
export type ProvenanceTone = 'brand' | 'secondary' | 'tertiary';

export interface ProvenanceRow {
  key: string;
  headline: string;
  tierLabel: string;
  tone: ProvenanceTone;
  epistemicLabel: string;
}

const TIER_LABEL: Record<Tier, string> = {
  high: 'High confidence',
  moderate: 'Moderate confidence',
  low: 'Low confidence',
  minimal: 'Minimal confidence',
  unscored: 'Unscored',
};

// Restraint by design (control-screen philosophy): only the strongest tier
// carries the accent; everything else stays in the grey ramp.
const TIER_TONE: Record<Tier, ProvenanceTone> = {
  high: 'brand',
  moderate: 'secondary',
  low: 'tertiary',
  minimal: 'tertiary',
  unscored: 'tertiary',
};

const EPISTEMIC_LABEL: Record<Epistemic, string> = {
  fact: 'Fact',
  claim: 'Claim',
  rumor: 'Rumor',
  speculation: 'Speculation',
  opinion: 'Opinion',
  unclassified: 'Unclassified',
};

export function presentProvenance(
  entries: PublicationCitationSnapshot[],
): ProvenanceRow[] {
  // Server order (snapshotted confidence DESC) is preserved as-is.
  return entries.map((e) => ({
    key: e.intelligenceObjectId,
    headline: e.headline,
    tierLabel: TIER_LABEL[e.confidenceTier] ?? TIER_LABEL.unscored,
    tone: TIER_TONE[e.confidenceTier] ?? 'tertiary',
    epistemicLabel: EPISTEMIC_LABEL[e.epistemicType] ?? EPISTEMIC_LABEL.unclassified,
  }));
}

/** Footer note anchoring the values to the publish moment, not the present. */
export function snapshotNote(entries: PublicationCitationSnapshot[]): string {
  const first = entries[0]?.snapshottedAt;
  const d = first ? new Date(first) : null;
  if (!d || Number.isNaN(d.getTime())) {
    return 'As verified at publish time';
  }
  const day = d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
  return `As verified at publish time · ${day}`;
}

/** Toggle label for the expandable section on a publication card. */
export function provenanceSummary(count: number): string {
  if (count === 0) return 'No cited sources';
  return count === 1 ? '1 verified source' : `${count} verified sources`;
}
