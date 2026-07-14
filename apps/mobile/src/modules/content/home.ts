import type { ContentDraft, DraftStatus } from '@oryx/shared-types';
import { DRAFT_STATUS_LABEL, FORMAT_LABEL } from './theme/draftColors';

/**
 * Content Studio home presenters — pure, node:test-testable (the screen-logic
 * extraction convention).
 *
 * Every value here traces to a real ContentDraft field (shared-types
 * drafts.ts:32-47): format, title, status, currentVersion, wordCount|null,
 * createdAt/updatedAt. The list payload has NO per-draft channel data — the
 * reference queue row's mono channel line comes from its mock's `ch` array;
 * real channels exist only as Publication.targetId → PublishTarget.channel
 * for already-published drafts and are not in GET /drafts. So the CS-2 row
 * renders real format/word-count/version meta instead, and no channel list
 * is invented (the RW-1 honesty rule).
 */

export interface ContentAction {
  id: string;
  label: string;
  /** Content-stack screen name — the same literals the old buttons navigated. */
  screen: string;
  primary?: boolean;
}

const GENERATE: ContentAction = {
  id: 'generate',
  label: 'Generate from packet',
  screen: 'GenerateDraft',
  primary: true,
};

/**
 * The CS-1 toolbar registry — one entry per action the five stacked buttons
 * carried (ContentHomeScreen pre-rebuild, lines 23-76). Action parity is
 * tested against this list; the screen maps it and navigates by entry, so an
 * action cannot be dropped without failing the parity test.
 */
export const CONTENT_ACTIONS: readonly ContentAction[] = [
  GENERATE,
  { id: 'review', label: 'Review queue', screen: 'ReviewQueue' },
  { id: 'targets', label: 'Publish targets', screen: 'PublishTargets' },
  { id: 'history', label: 'History', screen: 'PublishHistory' },
  { id: 'calendar', label: 'Calendar', screen: 'Calendar' },
];

/** The empty-state CTA reuses the real generate action, not a second literal. */
export const GENERATE_ACTION = GENERATE;

/**
 * Draft status → chip treatment, exhaustive on the real DraftStatus union (a
 * new status fails type-check here instead of rendering blank). Families
 * follow the reference queue chips (content.jsx:124 — approved/scheduled →
 * teal, review → warn) extended over the full union along the existing
 * draftColors semantics: published shares the positive family, rejected is
 * the negative, draft/archived recede to the plain chip.
 */
export function draftStatusChip(status: DraftStatus): {
  label: string;
  tone: 'positive' | 'warn' | 'negative' | 'neutral';
} {
  const label = DRAFT_STATUS_LABEL[status].toUpperCase();
  switch (status) {
    case 'approved':
    case 'scheduled':
    case 'published':
      return { label, tone: 'positive' };
    case 'in_review':
    case 'changes_requested':
      return { label, tone: 'warn' };
    case 'rejected':
      return { label, tone: 'negative' };
    case 'draft':
    case 'archived':
      return { label, tone: 'neutral' };
  }
}

/**
 * The fixed-width mono timestamp column ("2026-07-13") from the real
 * updatedAt. The reference queue's "09:30 ET" slot is a scheduled send time —
 * no such field exists on ContentDraft, so the honest equivalent is the real
 * last-updated date. Unparseable input renders no date rather than a fake.
 */
export function draftUpdatedDate(
  d: Pick<ContentDraft, 'updatedAt'>,
): string | undefined {
  const t = new Date(d.updatedAt);
  if (Number.isNaN(t.getTime())) return undefined;
  return t.toISOString().slice(0, 10);
}

/**
 * The row's mono meta line — real fields only: format label, word count when
 * the backend has one, and the real version number ("ARTICLE · 312 WORDS ·
 * v3"). This is the slot the reference fills with its mock channel list; see
 * the module note for why that is not reproducible.
 */
export function draftMeta(
  d: Pick<ContentDraft, 'format' | 'wordCount' | 'currentVersion'>,
): string {
  const parts = [FORMAT_LABEL[d.format].toUpperCase()];
  if (d.wordCount != null) parts.push(`${d.wordCount} WORDS`);
  parts.push(`v${d.currentVersion}`);
  return parts.join(' · ');
}

/**
 * The card-header mono sub ("3 DRAFTS") — same rules as workspaceCountSub:
 * silent while the query has no data, a real zero stated plainly.
 */
export function draftCountSub(
  drafts: ContentDraft[] | undefined,
): string | undefined {
  if (drafts === undefined) return undefined;
  return `${drafts.length} ${drafts.length === 1 ? 'DRAFT' : 'DRAFTS'}`;
}
