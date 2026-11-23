/**
 * Research Workspace design-foundation wave (RW-1..RW-4, 2026-07-13) — row
 * presenters, query-state correctness, the RW-3 token-violation fix, and the
 * honest deferral of RW-2.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  statusChip,
  workspaceCountSub,
  workspaceListState,
  workspaceMeta,
  workspaceRowId,
} from './list';

const stripComments = (src: string): string =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const read = (rel: string): string =>
  stripComments(readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf8'));

const WORKSPACE = {
  id: '337f1ae1-880a-49b0-9033-fe36485072e0',
  accountId: 'acc-1',
  workspaceId: 'ws-1',
  name: 'Oryx Coverage',
  description: null,
  status: 'active' as const,
  createdAt: '2026-07-13T00:00:00Z',
  updatedAt: '2026-07-13T09:15:00Z',
};

// ---- Query-state correctness -------------------------------------------------

test('workspaceListState distinguishes unresolved, failed, confirmed-empty and ready states', () => {
  assert.equal(workspaceListState(undefined, true, false), 'loading');
  assert.equal(workspaceListState(undefined, false, true), 'error');
  assert.equal(workspaceListState([], false, false), 'empty');
  assert.equal(workspaceListState([WORKSPACE], false, false), 'ready');
});

test('cached workspaces remain authoritative during a background refresh error', () => {
  assert.equal(workspaceListState([WORKSPACE], false, true), 'ready');
  assert.equal(workspaceListState([], false, true), 'empty');
});

test('unresolved no-data state never becomes a false empty state', () => {
  assert.equal(workspaceListState(undefined, false, false), 'loading');
});

// ---- RW-1 presenters --------------------------------------------------------

test('workspaceRowId renders the real uuid as a fixed mono display id, never a made-up serial', () => {
  assert.equal(workspaceRowId('337f1ae1-880a-49b0-9033-fe36485072e0'), 'RWS-337F1AE1');
  assert.equal(workspaceRowId('337f1ae1-880a-49b0-9033-fe36485072e0'), 'RWS-337F1AE1');
});

test('statusChip maps both real lifecycle statuses and nothing else — active is positive, archived recedes', () => {
  assert.deepEqual(statusChip('active'), { label: 'ACTIVE', tone: 'positive' });
  assert.deepEqual(statusChip('archived'), { label: 'ARCHIVED', tone: 'neutral' });
});

test('workspaceMeta uses only the real updatedAt timestamp and renders nothing for an unparseable one', () => {
  assert.equal(workspaceMeta({ updatedAt: '2026-07-13T09:15:00Z' }), 'UPDATED 2026-07-13');
  assert.equal(workspaceMeta({ updatedAt: 'not-a-date' }), undefined);
});

test('workspaceCountSub stays silent while loading, states a real zero plainly, and pluralizes', () => {
  assert.equal(workspaceCountSub(undefined), undefined);
  assert.equal(workspaceCountSub([]), '0 WORKSPACES');
  assert.equal(workspaceCountSub([WORKSPACE]), '1 WORKSPACE');
  assert.equal(workspaceCountSub([WORKSPACE, { ...WORKSPACE, id: 'd' }]), '2 WORKSPACES');
});

// ---- RW-3: the token-violation fix ------------------------------------------

test('RW-3 fixed: no hardcoded hex or rgba color remains anywhere in the touched files', () => {
  for (const rel of ['./screens/ResearchWorkspaceListScreen.tsx', './components/WorkspaceCard.tsx']) {
    const source = read(rel);
    assert.ok(!/rgba?\(/.test(source), `${rel}: no rgba()/rgb() literals`);
    assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(source), `${rel}: no hex literals`);
    assert.ok(!source.includes('borderRadius: 10'), `${rel}: no off-scale radius`);
  }
});

test('the input surface is built from the real tokens (elev bg, default border, radius scale, spacing scale)', () => {
  const source = read('./screens/ResearchWorkspaceListScreen.tsx');
  assert.ok(source.includes('theme.colors.bg.elevated'), 'input bg is --elev');
  assert.ok(source.includes('theme.colors.border.default'), 'input border is --border');
  assert.ok(source.includes('theme.radius.md'), 'radius from the scale');
  assert.ok(source.includes('theme.spacing[3]'), 'padding from the scale');
});

// ---- RW-1 anatomy + RW-2 deferral -------------------------------------------

test('workspace rows render through CardHeader + HairlineRowList with the mono-id + status-chip anatomy', () => {
  const screen = read('./screens/ResearchWorkspaceListScreen.tsx');
  assert.ok(screen.includes('<CardHeader title="Workspaces"'), 'real CardHeader');
  assert.ok(screen.includes('workspaceCountSub'), 'header sub is the real count');
  assert.ok(screen.includes('<HairlineRowList>'), 'rows pack through HairlineRowList');
  assert.ok(screen.includes('listState === \'error\''), 'request failures have a distinct error branch');
  assert.ok(screen.includes('workspaces.refetch()'), 'the error state can retry');
  const row = read('./components/WorkspaceCard.tsx');
  assert.ok(row.includes('workspaceRowId'), 'row leads with the real mono id');
  assert.ok(row.includes('gx.chip') && row.includes('gx.chipTeal'), 'status chip anatomy');
  assert.ok(row.includes('useGx()'), 'gx resolves through useGx() (theme-aware)');
  assert.ok(!/import\s*\{[^}]*\bgx\b[^}]*\}/.test(row), 'no static gx import remains');
  assert.ok(row.includes('workspaceMeta'), 'mono meta from real timestamps');
  assert.ok(!/claims?Count|ownerName/i.test(row), 'no invented claim/owner fields');
});

test('RW-2 deferred honestly: no selected/active-row treatment is invented — no real concept backs one', () => {
  for (const rel of ['./screens/ResearchWorkspaceListScreen.tsx', './components/WorkspaceCard.tsx']) {
    const source = read(rel);
    assert.ok(!/selected|activeRow|navActiveBar/i.test(source), `${rel}: no fake selected state`);
  }
});
