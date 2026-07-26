import type { IconName } from '@oryx/design-system';
import type { WorkspaceActivityEvent } from '@oryx/shared-types';

function shortId(id: string): string {
  return id.length <= 8 ? id : `${id.slice(0, 8)}…`;
}

function title(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1);
}

function who(accountId: string | null, meAccountId: string | undefined): string {
  if (!accountId) return 'Someone';
  return accountId === meAccountId ? 'You' : shortId(accountId);
}

export interface ActivityCopy {
  icon: IconName;
  text: string;
}

/**
 * Exhaustive switch over WorkspaceActivityEventType, no default branch — same
 * convention as automation/feed.ts's ACTION_COPY: a future event kind fails
 * type-check here until this is updated. 'role_changed' is now real
 * (role-change wave) — every real emission sets `previousRole`, so the copy
 * states the honest from/to transition rather than just the new role.
 */
export function describeActivityEvent(
  event: WorkspaceActivityEvent,
  meAccountId: string | undefined,
): ActivityCopy {
  switch (event.event) {
    case 'member_invited':
      return {
        icon: 'UserPlus',
        text: `${event.subjectEmail ?? 'Someone'} was invited as ${title(event.role ?? '')}`,
      };
    case 'member_joined':
      return {
        icon: 'UserCheck',
        text: `${who(event.subjectAccountId, meAccountId)} joined as ${title(event.role ?? '')}`,
      };
    case 'member_removed':
      return {
        icon: 'UserMinus',
        text: `${who(event.subjectAccountId, meAccountId)} was removed`,
      };
    case 'role_changed':
      return {
        icon: 'Shield',
        text: event.previousRole
          ? `${who(event.subjectAccountId, meAccountId)}'s role changed from ${title(event.previousRole)} to ${title(event.role ?? '')}`
          : `${who(event.subjectAccountId, meAccountId)}'s role changed to ${title(event.role ?? '')}`,
      };
  }
}
