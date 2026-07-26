/**
 * Workspace-pill dropdown — the pure model the sidebar renders.
 *
 * Team/Workspace Rev 2 shipped real multi-workspace membership + switching,
 * so this is now a real switcher: any OTHER real workspace passed in renders
 * as a 'switch:<id>' item above Account settings / Sign out. These tests
 * replace the old single-workspace-only pin (2026-07-12) now that a second
 * workspace is a real, reachable state, not a hypothetical.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { workspaceMenu } from './workspaceMenu';

const me = {
  workspace: {
    id: 'ws-1',
    name: 'Krishna Mishra',
    kind: 'personal' as const,
    role: 'owner' as const,
  },
};

test('menu header shows the real workspace name and kind + role meta from /me', () => {
  const menu = workspaceMenu(me);
  assert.equal(menu.name, 'Krishna Mishra');
  assert.equal(menu.meta, 'Personal workspace · Owner');
});

test('with only one real workspace, the menu offers exactly Account settings and Sign out', () => {
  const menu = workspaceMenu(me, [
    { id: 'ws-1', name: 'Krishna Mishra', kind: 'personal', role: 'owner' },
  ]);
  assert.deepEqual(
    menu.items.map((i) => i.id),
    ['account', 'signout'],
  );
});

test('a second real workspace renders as a switch item above account/signout', () => {
  const menu = workspaceMenu(me, [
    { id: 'ws-1', name: 'Krishna Mishra', kind: 'personal', role: 'owner' },
    { id: 'ws-2', name: 'ORYX Research Team', kind: 'team', role: 'editor' },
  ]);
  assert.deepEqual(
    menu.items.map((i) => i.id),
    ['switch:ws-2', 'account', 'signout'],
  );
  const switchItem = menu.items[0]!;
  assert.equal(switchItem.label, 'ORYX Research Team');
  assert.equal(switchItem.sub, 'Team · Editor');
});

test('the current workspace never appears as its own switch target', () => {
  const menu = workspaceMenu(me, [
    { id: 'ws-1', name: 'Krishna Mishra', kind: 'personal', role: 'owner' },
  ]);
  assert.ok(!menu.items.some((i) => i.id === 'switch:ws-1'));
});

test('multiple other workspaces all render as switch items, each keyed by its own id', () => {
  const menu = workspaceMenu(me, [
    { id: 'ws-1', name: 'Krishna Mishra', kind: 'personal', role: 'owner' },
    { id: 'ws-2', name: 'ORYX Research Team', kind: 'team', role: 'editor' },
    { id: 'ws-3', name: 'Side Project', kind: 'team', role: 'admin' },
  ]);
  assert.deepEqual(
    menu.items.map((i) => i.id),
    ['switch:ws-2', 'switch:ws-3', 'account', 'signout'],
  );
});
