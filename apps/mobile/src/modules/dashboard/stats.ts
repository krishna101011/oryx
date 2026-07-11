import type { IntakeStatusSummary } from '@oryx/shared-types';

/**
 * Command Center stat presenters — pure, node:test-testable (the screen-logic
 * extraction convention).
 *
 * The SOURCES stat reads GET /intake/status. While the query has no data yet
 * it shows '—', never a fake zero: a workspace with three sources must not
 * flash "0" during load, and a real zero still renders as '0'.
 */
export function sourcesStatValue(status: IntakeStatusSummary | undefined): string {
  return status ? String(status.total) : '—';
}
