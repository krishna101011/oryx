/**
 * Web command-bar search (2026-07-12) — the pure filter behind the ⌘K overlay.
 *
 * DELIBERATELY SCOPED to what actually exists today: the workspace's
 * connected sources (GET /intake/sources) and its recent ingested items
 * (GET /intake/items/recent). Full cross-entity search (claims, drafts,
 * markets) is future scope — the overlay says so in plain copy rather than
 * pretending those are searchable. Pure module: node:test-testable.
 */
import type { IntakeSource, RecentIntakeItem } from '@oryx/shared-types';

/** Per-group result cap — a command palette shows a short list, not a page. */
export const SEARCH_GROUP_CAP = 8;

export interface SearchResults {
  sources: IntakeSource[];
  items: RecentIntakeItem[];
}

function matches(haystack: string | null | undefined, needle: string): boolean {
  return (haystack ?? '').toLowerCase().includes(needle);
}

/**
 * Case-insensitive substring filter. A blank query returns nothing (the
 * overlay shows its scope hint instead of dumping everything). Sources match
 * on name or kind; items on subject, source name, or provider.
 */
export function searchWorkspace(
  query: string,
  sources: IntakeSource[],
  items: RecentIntakeItem[],
): SearchResults {
  const needle = query.trim().toLowerCase();
  if (needle.length === 0) return { sources: [], items: [] };
  return {
    sources: sources
      .filter((s) => matches(s.name, needle) || matches(s.kind, needle))
      .slice(0, SEARCH_GROUP_CAP),
    items: items
      .filter(
        (i) =>
          matches(i.subject, needle) ||
          matches(i.sourceName, needle) ||
          matches(i.providerName, needle),
      )
      .slice(0, SEARCH_GROUP_CAP),
  };
}
