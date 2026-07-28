import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import type { ChatMessage } from '@oryx/shared-types';
import { chatApi } from '../api/chat';
import {
  type ChatPollState,
  INITIAL_CHAT_POLL_STATE,
  applyPollResult,
  markDeletedLocally,
  sinceParamFor,
  upsertMessage,
} from '../chatPolling';

export const CHAT_MESSAGES_KEY = ['workspace', 'chat', 'messages'];
const POLL_INTERVAL_MS = 5000;

/**
 * Single-channel workspace chat: polling via refetchInterval (same
 * mechanism as useIntakeStatus, the app's only other polling precedent),
 * cursor-narrowed via chatPolling's pure state machine so a 5s poll asks
 * for "what's new since <cursor>" instead of re-fetching the whole latest
 * page every tick. `messages` is component state (not the react-query
 * cache) because it accumulates across pages — the cache only ever holds
 * the MOST RECENT poll response.
 */
export function useTeamChat() {
  const stateRef = useRef<ChatPollState>(INITIAL_CHAT_POLL_STATE);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const query = useQuery({
    queryKey: CHAT_MESSAGES_KEY,
    queryFn: () => chatApi.listMessages(sinceParamFor(stateRef.current)),
    refetchInterval: POLL_INTERVAL_MS,
  });

  useEffect(() => {
    if (!query.data) return;
    stateRef.current = applyPollResult(stateRef.current, query.data);
    setMessages(stateRef.current.messages);
  }, [query.data]);

  const sendMessage = useMutation({
    mutationFn: (body: string) => chatApi.sendMessage(body),
    onSuccess: (message) => {
      stateRef.current = { ...stateRef.current, messages: upsertMessage(stateRef.current.messages, message) };
      setMessages(stateRef.current.messages);
    },
  });

  const editMessage = useMutation({
    mutationFn: ({ messageId, body }: { messageId: string; body: string }) =>
      chatApi.editMessage(messageId, body),
    onSuccess: (message) => {
      stateRef.current = { ...stateRef.current, messages: upsertMessage(stateRef.current.messages, message) };
      setMessages(stateRef.current.messages);
    },
  });

  const deleteMessage = useMutation({
    mutationFn: (messageId: string) => chatApi.deleteMessage(messageId),
    onSuccess: (_result, messageId) => {
      stateRef.current = {
        ...stateRef.current,
        messages: markDeletedLocally(stateRef.current.messages, messageId, new Date().toISOString()),
      };
      setMessages(stateRef.current.messages);
    },
  });

  return {
    messages,
    isLoading: query.isLoading,
    error: query.error,
    sendMessage,
    editMessage,
    deleteMessage,
  };
}
