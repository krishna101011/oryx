import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { WorkspaceActivityEvent } from '@oryx/shared-types';
import { describeActivityEvent } from './activityCopy';

const ME = 'acc-me';

function event(overrides: Partial<WorkspaceActivityEvent>): WorkspaceActivityEvent {
  return {
    id: 'evt-1',
    event: 'member_invited',
    actorAccountId: null,
    subjectAccountId: null,
    subjectEmail: null,
    role: null,
    previousRole: null,
    createdAt: '2026-07-26T00:00:00Z',
    ...overrides,
  };
}

test('member_invited: shows the real invited email and role, never an account id', () => {
  const copy = describeActivityEvent(
    event({ event: 'member_invited', subjectEmail: 'friend@oryx.test', role: 'editor' }),
    ME,
  );
  assert.equal(copy.icon, 'UserPlus');
  assert.equal(copy.text, 'friend@oryx.test was invited as Editor');
});

test('member_joined: the current account renders as "You", not its own id', () => {
  const copy = describeActivityEvent(
    event({ event: 'member_joined', subjectAccountId: ME, role: 'admin' }),
    ME,
  );
  assert.equal(copy.icon, 'UserCheck');
  assert.equal(copy.text, 'You joined as Admin');
});

test('member_joined: a different account renders as a shortened id, not the full uuid', () => {
  const copy = describeActivityEvent(
    event({ event: 'member_joined', subjectAccountId: 'acc-0123456789abcdef', role: 'reader' }),
    ME,
  );
  assert.equal(copy.text, 'acc-0123… joined as Reader');
});

test('member_removed: no role suffix, current account still resolves to "You"', () => {
  const copy = describeActivityEvent(
    event({ event: 'member_removed', subjectAccountId: ME, role: 'editor' }),
    ME,
  );
  assert.equal(copy.icon, 'UserMinus');
  assert.equal(copy.text, 'You was removed');
});

test('role_changed: real emissions always carry previousRole, so the copy states the honest from/to transition', () => {
  const copy = describeActivityEvent(
    event({
      event: 'role_changed',
      subjectAccountId: 'acc-999999999999',
      role: 'admin',
      previousRole: 'editor',
    }),
    ME,
  );
  assert.equal(copy.icon, 'Shield');
  assert.equal(copy.text, "acc-9999…'s role changed from Editor to Admin");
});

test('role_changed: a null previousRole (should not happen for a real emission, but stays honest) falls back to "changed to"', () => {
  const copy = describeActivityEvent(
    event({ event: 'role_changed', subjectAccountId: 'acc-999999999999', role: 'admin' }),
    ME,
  );
  assert.equal(copy.text, "acc-9999…'s role changed to Admin");
});

test('a null subject account (should not happen for joined/removed, but stays honest) renders as "Someone"', () => {
  const copy = describeActivityEvent(
    event({ event: 'member_removed', subjectAccountId: null, role: 'reader' }),
    ME,
  );
  assert.equal(copy.text, 'Someone was removed');
});
