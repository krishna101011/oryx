/**
 * Pure cursor/merge logic behind useTeamChat's poll loop — no rendering, no
 * timers (mobile has no fake-timer infra; see the "FRONTEND TESTS:
 * PURE-LOGIC ONLY" convention). Proves the property the task specifically
 * asked to confirm rather than assume: after a first page lands, the NEXT
 * request's `since` is that page's real cursor, not omitted — so a poll
 * narrows to "what's new" instead of re-fetching the whole latest page
 * every tick.
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { ApiResponse, ChatMessage } from '@oryx/shared-types';
import {
  applyPollResult,
  INITIAL_CHAT_POLL_STATE,
  markDeletedLocally,
  sinceParamFor,
  upsertMessage,
} from './chatPolling';

function msg(id: string, body: string, createdAt: string): ChatMessage {
  return {
    id,
    workspaceId: 'ws-1',
    senderAccountId: 'acc-1',
    body,
    createdAt,
    editedAt: null,
    deletedAt: null,
  };
}

function page(data: ChatMessage[], nextCursor: string | null): ApiResponse<ChatMessage[]> {
  return { data, meta: { requestId: 'r', serverTime: '2026-07-27T00:00:00Z', pagination: { nextCursor, prevCursor: null } } };
}

test('the very first request has no cursor to send', () => {
  assert.equal(sinceParamFor(INITIAL_CHAT_POLL_STATE), undefined);
});

test('after the first page lands, the next request passes ITS cursor — not omitted, not the same as the first', () => {
  const first = page([msg('m1', 'hello', '2026-07-27T00:00:00Z')], 'cursor-1');
  const state1 = applyPollResult(INITIAL_CHAT_POLL_STATE, first);

  assert.equal(sinceParamFor(state1), 'cursor-1', 'second request must carry the real cursor from the first response');
  assert.notEqual(sinceParamFor(state1), undefined, 'second request must NOT omit since (that would re-fetch the whole history)');
});

test('a quiet poll (no new messages) still advances/holds the cursor instead of resetting to null', () => {
  const state1 = applyPollResult(INITIAL_CHAT_POLL_STATE, page([msg('m1', 'hi', '2026-07-27T00:00:00Z')], 'cursor-1'));
  const quiet = page([], 'cursor-1'); // backend hands back the SAME cursor when nothing new
  const state2 = applyPollResult(state1, quiet);

  assert.equal(sinceParamFor(state2), 'cursor-1');
  assert.equal(state2.messages.length, 1, 'no messages lost on an empty poll');
});

test('a real second poll with new messages advances the cursor to the new one and appends without duplicating', () => {
  const state1 = applyPollResult(INITIAL_CHAT_POLL_STATE, page([msg('m1', 'first', '2026-07-27T00:00:00Z')], 'cursor-1'));
  const state2 = applyPollResult(state1, page([msg('m2', 'second', '2026-07-27T00:01:00Z')], 'cursor-2'));

  assert.deepEqual(state2.messages.map((m) => m.body), ['first', 'second']);
  assert.equal(sinceParamFor(state2), 'cursor-2');
});

test('upsertMessage replaces an existing id (edit) instead of duplicating the row', () => {
  const withOne = upsertMessage([], msg('m1', 'original', '2026-07-27T00:00:00Z'));
  const edited = { ...withOne[0]!, body: 'corrected' };
  const after = upsertMessage(withOne, edited);

  assert.equal(after.length, 1);
  assert.equal(after[0]!.body, 'corrected');
});

test('markDeletedLocally redacts body and sets deletedAt for the target id only', () => {
  const messages = [msg('m1', 'keep me', '2026-07-27T00:00:00Z'), msg('m2', 'delete me', '2026-07-27T00:01:00Z')];
  const after = markDeletedLocally(messages, 'm2', '2026-07-27T00:02:00Z');

  assert.equal(after[0]!.body, 'keep me');
  assert.equal(after[1]!.body, null);
  assert.equal(after[1]!.deletedAt, '2026-07-27T00:02:00Z');
});
