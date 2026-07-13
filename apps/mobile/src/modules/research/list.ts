import type { ResearchWorkspace } from '@oryx/shared-types';

/**
 * Research Workspace list presenters — pure, node:test-testable (the
 * screen-logic extraction convention).
 *
 * Every value here traces to a real ResearchWorkspace field (shared-types
 * research.ts:12-21): id, name, description|null, status 'active'|'archived',
 * createdAt/updatedAt. The type has NO claim count, NO owner display name
 * (accountId is a bare uuid), and the list endpoint returns no item counts —
 * so the RW-1 meta line is built from the real timestamps, and nothing else
 * is invented.
 */

/**
 * Mono display id for a row ("RWS-337F1AE1") — a fixed-width rendering of the
 * workspace's REAL uuid (first 8 hex chars, uppercase), not a made-up serial.
 */
export function workspaceRowId(id: string): string {
  return `RWS-${id.replace(/-/g, '').slice(0, 8).toUpperCase()}`;
}

/** The two real lifecycle statuses → chip treatment. 'active' takes the teal
 * (positive-text) chip; 'archived' recedes to the plain chip. Exhaustive on
 * the union — a new status fails type-check here instead of rendering blank. */
export function statusChip(status: ResearchWorkspace['status']): {
  label: string;
  tone: 'positive' | 'neutral';
} {
  switch (status) {
    case 'active':
      return { label: 'ACTIVE', tone: 'positive' };
    case 'archived':
      return { label: 'ARCHIVED', tone: 'neutral' };
  }
}

/**
 * Mono meta line from the real updatedAt timestamp ("UPDATED 2026-07-13").
 * Claims/owner meta per the reference is NOT reproducible from real fields
 * (none exist on ResearchWorkspace) — the timestamp is what we honestly have.
 * An unparseable timestamp renders no meta rather than a fake date.
 */
export function workspaceMeta(w: Pick<ResearchWorkspace, 'updatedAt'>): string | undefined {
  const d = new Date(w.updatedAt);
  if (Number.isNaN(d.getTime())) return undefined;
  return `UPDATED ${d.toISOString().slice(0, 10)}`;
}

/**
 * The card-header mono sub ("1 WORKSPACE") — same rules as the Command
 * Center's todayCountSub: silent while the query has no data, a real zero
 * stated plainly.
 */
export function workspaceCountSub(
  workspaces: ResearchWorkspace[] | undefined,
): string | undefined {
  if (workspaces === undefined) return undefined;
  return `${workspaces.length} ${workspaces.length === 1 ? 'WORKSPACE' : 'WORKSPACES'}`;
}
