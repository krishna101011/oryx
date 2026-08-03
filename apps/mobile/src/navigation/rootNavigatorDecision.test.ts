import assert from 'node:assert/strict';
import { test } from 'node:test';
import { decideRootBranch } from './rootNavigatorDecision';

test('unresolved route always shows splash, regardless of what it will resolve to', () => {
  assert.equal(decideRootBranch({ resolved: false, isPublicRoute: false }), 'splash');
  assert.equal(decideRootBranch({ resolved: false, isPublicRoute: true }), 'splash');
});

test('a resolved public route always picks "public" — checked before any auth branch', () => {
  assert.equal(decideRootBranch({ resolved: true, isPublicRoute: true }), 'public');
});

test('a resolved non-public route falls through to the auth-gated branch', () => {
  assert.equal(decideRootBranch({ resolved: true, isPublicRoute: false }), 'auth-gated');
});
