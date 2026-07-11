/**
 * Workspace-pill dropdown model (2026-07-12) — pure, node:test-testable.
 *
 * HONESTLY SCOPED: exactly one workspace exists per account today (the
 * personal workspace; Team/Workspace deepening is frozen architecture, not
 * built), so this is deliberately NOT a workspace switcher — there is nothing
 * to switch to. The menu states the current workspace as fact and offers the
 * two actions that are real: Account settings and Sign out. There is no
 * plan/billing tier yet either (a known roadmap gap), so the meta line shows
 * the workspace kind + the member's role — the two real facts /me carries.
 */
import type { MeResponse } from '@oryx/shared-types';

export type WorkspaceMenuAction = 'account' | 'signout';

export interface WorkspaceMenuModel {
  /** Current workspace name, verbatim from /me. */
  name: string;
  /** "Personal workspace · Owner" — kind + role, the real /me facts. */
  meta: string;
  /** The honest single-workspace statement shown under the header. */
  note: string;
  items: { id: WorkspaceMenuAction; label: string }[];
}

function title(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1);
}

export function workspaceMenu(me: Pick<MeResponse, 'workspace'>): WorkspaceMenuModel {
  return {
    name: me.workspace.name,
    meta: `${title(me.workspace.kind)} workspace · ${title(me.workspace.role)}`,
    note: 'Your only workspace — switching arrives with Teams.',
    items: [
      { id: 'account', label: 'Account settings' },
      { id: 'signout', label: 'Sign out' },
    ],
  };
}
