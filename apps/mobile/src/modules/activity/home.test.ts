import assert from 'node:assert/strict';
import { test } from 'node:test';
import { activityInboxState } from './home';

test('activityInboxState distinguishes loading, error, confirmed-empty and ready', () => {
  assert.equal(activityInboxState(undefined, false), 'loading');
  assert.equal(activityInboxState(undefined, true), 'error');
  assert.equal(activityInboxState([], false), 'empty');
  assert.equal(activityInboxState([{ id: 'row-1' } as never], false), 'ready');
});

test('cached activity remains visible when a background refresh fails', () => {
  assert.equal(activityInboxState([{ id: 'row-1' } as never], true), 'ready');
  assert.equal(activityInboxState([], true), 'empty');
});
