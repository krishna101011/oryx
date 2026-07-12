import type { IntakeStatusSummary, MeResponse, RecentIntakeItem } from '@oryx/shared-types';
import type { SettingsStackParamList } from '../../navigation/types';

/**
 * Command Center stat + Today-panel presenters — pure, node:test-testable
 * (the screen-logic extraction convention).
 *
 * Every stat shows '—' while its query has no data yet, never a fake zero:
 * a workspace with three sources must not flash "0" during load, and a real
 * zero still renders as '0'.
 */
export function sourcesStatValue(status: IntakeStatusSummary | undefined): string {
  return status ? String(status.total) : '—';
}

/**
 * VERIFIED — intelligence objects with verification_status 'verified' or
 * 'analyst_approved' (see MeResponse.verification.verifiedCount; approval
 * replaces 'verified', so both statuses mean verified). Claims carry no
 * verification status — objects are the per-item verdict unit.
 */
export function verifiedStatValue(me: Pick<MeResponse, 'verification'> | undefined): string {
  return me ? String(me.verification.verifiedCount) : '—';
}

/** DRAFTS — MeResponse.content.draftCount (every draft in the workspace). */
export function draftsStatValue(me: Pick<MeResponse, 'content'> | undefined): string {
  return me ? String(me.content.draftCount) : '—';
}

// ---------------------------------------------------------------------------
// "Today" panel — the real recently-ingested content (headline + source) from
// GET /v1/intake/items/recent, NOT the activity_inbox rows: those are all the
// identical system notification "New item ingested" with no content, which is
// the Activity screen's job to show. Today answers "what came in".
// ---------------------------------------------------------------------------

export interface TodayRow {
  id: string;
  headline: string;
  source: string;
  receivedAt: string;
}

export type TodayPanelState =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'list'; rows: TodayRow[] };

export const TODAY_MAX_ROWS = 6;

/**
 * While the query has no data the panel must not flash the "connect a source"
 * empty copy (same rule as the fake-zero stats); a loaded-but-empty feed shows
 * it; items render newest-first as the server returned them, capped so the
 * panel stays a brief, not a feed.
 */
export function todayPanelState(
  items: RecentIntakeItem[] | undefined,
  max: number = TODAY_MAX_ROWS,
): TodayPanelState {
  if (items === undefined) return { kind: 'loading' };
  if (items.length === 0) return { kind: 'empty' };
  return {
    kind: 'list',
    rows: items.slice(0, max).map((i) => ({
      id: i.id,
      // A not-yet-normalized item has no subject; never render a blank line.
      headline: i.subject?.trim() ? i.subject.trim() : 'Untitled item',
      source: i.sourceName,
      receivedAt: i.receivedAt,
    })),
  };
}

/**
 * Where a Today-row press lands (2026-07-12). TodayRow.id IS the intake item
 * id — /items/recent returns `"id": str(item.id)` and todayPanelState maps it
 * 1:1 — so a press opens the SAME IntakeItemDetail screen Activity rows and
 * search results open (SettingsStack registers exactly one ItemDetailScreen
 * for that name). The params type is taken from SettingsStackParamList, so a
 * drift from the real route's shape fails type-check, not at runtime.
 */
export function todayRowTarget(row: Pick<TodayRow, 'id'>): {
  screen: 'IntakeItemDetail';
  params: SettingsStackParamList['IntakeItemDetail'];
} {
  return { screen: 'IntakeItemDetail', params: { itemId: row.id } };
}
