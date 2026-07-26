/**
 * Workspace-pill dropdown model — pure, node:test-testable.
 *
 * Team/Workspace Rev 2 shipped multi-workspace membership, invites, and
 * switching (docs/TEAM_WORKSPACE_ARCHITECTURE.md) — this is now a real
 * switcher: any other workspace the account actively belongs to (from
 * GET /workspaces) renders as a "switch:<id>" item above the Account
 * settings / Sign out actions. When exactly one workspace exists (still the
 * common case), the item list is unchanged from before — there is simply
 * nothing to switch to, and the model doesn't manufacture a placeholder row
 * to say so.
 */
import type { ActiveWorkspace, MeResponse } from '@oryx/shared-types';

export type WorkspaceMenuItemId = 'account' | 'signout' | `switch:${string}`;

export interface WorkspaceMenuItem {
  id: WorkspaceMenuItemId;
  label: string;
  /** Only set on switch items — the target workspace's kind + role. */
  sub?: string;
}

export interface WorkspaceMenuModel {
  /** Current workspace name, verbatim from /me. */
  name: string;
  /** "Personal workspace · Owner" — kind + role, the real /me facts. */
  meta: string;
  items: WorkspaceMenuItem[];
}

function title(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1);
}

export function workspaceMenu(
  me: Pick<MeResponse, 'workspace'>,
  workspaces: ActiveWorkspace[] = [],
): WorkspaceMenuModel {
  const switchItems: WorkspaceMenuItem[] = workspaces
    .filter((w) => w.id !== me.workspace.id)
    .map((w) => ({
      id: `switch:${w.id}` as const,
      label: w.name,
      sub: `${title(w.kind)} · ${title(w.role)}`,
    }));

  return {
    name: me.workspace.name,
    meta: `${title(me.workspace.kind)} workspace · ${title(me.workspace.role)}`,
    items: [
      ...switchItems,
      { id: 'account', label: 'Account settings' },
      { id: 'signout', label: 'Sign out' },
    ],
  };
}
