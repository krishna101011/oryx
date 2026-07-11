/**
 * Activity row → detail resolution (2026-07-12).
 *
 * Every activity_inbox row carries the raw triggering event payload in
 * `data`. For "New item ingested" rows (intake.item.received) that payload
 * includes intakeItemId — the key that lets the row open the REAL ingested
 * item instead of being a dead end. Pure module so the resolution is
 * node:test-testable without a component harness.
 */
import type { ActivityItem } from '@oryx/shared-types';

/**
 * The intake item a row can open, or null when the row has no item behind it
 * (security events, digests, verification/publishing notifications, malformed
 * payloads). Null means "this row is informational — pressing it only toggles
 * read state", which is the pre-existing behavior for every such row.
 */
export function intakeItemIdOf(item: Pick<ActivityItem, 'data'>): string | null {
  const id = item.data?.['intakeItemId'];
  return typeof id === 'string' && id.length > 0 ? id : null;
}
