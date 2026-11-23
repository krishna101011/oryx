import type { ActivityItem } from '@oryx/shared-types';

/** Activity inbox query states. Existing cached rows remain visible during a failed background refresh. */
export type ActivityInboxState = 'loading' | 'error' | 'empty' | 'ready';

export function activityInboxState(
  items: ActivityItem[] | undefined,
  isError: boolean,
): ActivityInboxState {
  if (items !== undefined) return items.length === 0 ? 'empty' : 'ready';
  if (isError) return 'error';
  return 'loading';
}
