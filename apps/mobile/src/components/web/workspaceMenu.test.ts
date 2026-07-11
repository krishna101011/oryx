/**
 * Workspace-pill dropdown — the pure model the sidebar renders.
 *
 * The dropdown is deliberately NOT a workspace switcher: one workspace exists
 * per account today (Team/Workspace architecture is frozen but unbuilt), so
 * the menu is current-workspace facts + Account settings + Sign out. These
 * tests pin that scope so a switcher can't sneak in half-built.
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

test('menu offers exactly Account settings and Sign out — and NO workspace switcher', () => {
  const menu = workspaceMenu(me);
  assert.deepEqual(
    menu.items.map((i) => i.id),
    ['account', 'signout'],
  );
  const labels = menu.items.map((i) => i.label.toLowerCase()).join(' ');
  assert.ok(!labels.includes('switch'), 'no switch item until a second workspace can exist');
  assert.ok(!labels.includes('create'), 'no create-workspace item either');
});

test('the single-workspace reality is stated in plain copy, not hidden', () => {
  const menu = workspaceMenu(me);
  assert.ok(menu.note.toLowerCase().includes('only workspace'));
});
