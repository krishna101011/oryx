import type {
  ApiResponse,
  ChatMessage,
  ChatReadMarker,
  EditChatMessageRequest,
  MarkChatReadRequest,
  SendChatMessageRequest,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

// Team Chat foundation wave's real endpoints (services/workspaces/router.py).
// listMessages uses getEnvelope so callers can read meta.pagination.nextCursor
// — the same CR-9 cursor contract useSourceAudit follows.
export const chatApi = {
  listMessages: (since?: string): Promise<ApiResponse<ChatMessage[]>> =>
    apiClient().getEnvelope<ChatMessage[]>(
      `/workspaces/messages${since ? `?since=${encodeURIComponent(since)}` : ''}`,
    ),

  sendMessage: (body: string): Promise<ChatMessage> =>
    apiClient().post<ChatMessage, SendChatMessageRequest>('/workspaces/messages', { body }),

  editMessage: (messageId: string, body: string): Promise<ChatMessage> =>
    apiClient().patch<ChatMessage, EditChatMessageRequest>(
      `/workspaces/messages/${messageId}`,
      { body },
    ),

  deleteMessage: (messageId: string): Promise<{ deleted: boolean }> =>
    apiClient().delete<{ deleted: boolean }>(`/workspaces/messages/${messageId}`),

  markRead: (messageId: string): Promise<ChatReadMarker> =>
    apiClient().post<ChatReadMarker, MarkChatReadRequest>('/workspaces/messages/read', {
      messageId,
    }),

  getReadMarker: (): Promise<ChatReadMarker> =>
    apiClient().get<ChatReadMarker>('/workspaces/messages/read'),
};
