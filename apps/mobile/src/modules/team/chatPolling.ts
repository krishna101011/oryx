import type { ApiResponse, ChatMessage } from '@oryx/shared-types';

/**
 * Pure cursor/merge logic for the Team chat poll loop — no react-query, no
 * timers, so it's directly unit-testable (mobile has no rendered-timer
 * infra; see the "FRONTEND TESTS: PURE-LOGIC ONLY" convention).
 *
 * `cursor` is the last `nextCursor` this client has seen. `null` means
 * "no page fetched yet" — the only state that omits `since` on the next
 * request. Once a first page lands, `cursor` is always a real string (the
 * backend hands back the SAME cursor, not null, when a poll finds nothing
 * new — see list_messages' `next_cursor = since` fallback), so every
 * request after the first one narrows to "only what's new."
 */
export interface ChatPollState {
  messages: ChatMessage[];
  cursor: string | null;
}

export const INITIAL_CHAT_POLL_STATE: ChatPollState = { messages: [], cursor: null };

/** What `since` query param the NEXT fetch should use — undefined only
 * before the very first page has ever landed. */
export function sinceParamFor(state: ChatPollState): string | undefined {
  return state.cursor ?? undefined;
}

/** Upsert-by-id, sorted oldest-first (matches the backend's created_at/id
 * cursor order) — an edit/re-send of an id already present replaces it in
 * place instead of duplicating the row. */
export function upsertMessage(existing: ChatMessage[], incoming: ChatMessage): ChatMessage[] {
  const withoutIncoming = existing.filter((m) => m.id !== incoming.id);
  return [...withoutIncoming, incoming].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
  );
}

function mergeMessages(existing: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  return incoming.reduce((acc, m) => upsertMessage(acc, m), existing);
}

/** Marks a message deleted locally (matches the backend's soft-delete
 * redaction: body -> null, deletedAt set) — used so a sender's own delete
 * reflects immediately without waiting on the next poll to surface it. */
export function markDeletedLocally(
  existing: ChatMessage[],
  messageId: string,
  deletedAt: string,
): ChatMessage[] {
  return existing.map((m) => (m.id === messageId ? { ...m, body: null, deletedAt } : m));
}

/** Applies one poll response to the running state. An empty page still
 * advances `cursor` when the response hands one back (it always does once
 * `state.cursor` is non-null) — so a quiet channel doesn't re-request the
 * whole history forever. */
export function applyPollResult(
  state: ChatPollState,
  response: ApiResponse<ChatMessage[]>,
): ChatPollState {
  const incoming = response.data;
  const nextCursor = response.meta?.pagination?.nextCursor ?? state.cursor;
  if (incoming.length === 0) {
    return { messages: state.messages, cursor: nextCursor };
  }
  return { messages: mergeMessages(state.messages, incoming), cursor: nextCursor };
}
