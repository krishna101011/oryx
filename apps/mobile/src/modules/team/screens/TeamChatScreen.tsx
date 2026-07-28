import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { ChatMessage } from '@oryx/shared-types';
import { useMe } from '../../../hooks/useMe';
import { useTeamChat } from '../hooks/useTeamChat';

function shortId(id: string): string {
  return id.length <= 8 ? id : `${id.slice(0, 8)}…`;
}

/**
 * Team Chat foundation wave's UI — a single workspace-wide channel, polled
 * every 5s (useTeamChat), reached from TeamHome. Same Card/HairlineRowList
 * anatomy as TeamActivityScreen rather than a chat-bubble layout, so it
 * reads as part of the same section, not a bolted-on messenger widget.
 * Edit/delete affordances only ever render for the sender's own messages —
 * mirroring the backend's real enforcement (router.py's
 * _get_own_message_or_error), not just a client-side nicety.
 */
export const TeamChatScreen: React.FC = () => {
  const t = useTheme();
  const me = useMe();
  const meId = me.data?.account.id;
  const { messages, isLoading, sendMessage, editMessage, deleteMessage } = useTeamChat();

  const [draft, setDraft] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState('');

  const onSend = () => {
    const body = draft.trim();
    if (!body) return;
    sendMessage.mutate(body, { onSuccess: () => setDraft('') });
  };

  const startEdit = (message: ChatMessage) => {
    setEditingId(message.id);
    setEditDraft(message.body ?? '');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft('');
  };

  const saveEdit = (messageId: string) => {
    const body = editDraft.trim();
    if (!body) return;
    editMessage.mutate(
      { messageId, body },
      { onSuccess: () => setEditingId(null) },
    );
  };

  return (
    <Screen background="primary">
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 0}
      >
        <ScrollView showsVerticalScrollIndicator={false} style={styles.flex}>
          <Spacer size={6} />
          <Text variant="pageTitle">Chat</Text>
          <Spacer size={2} />
          <Text variant="body" color="secondary">
            One channel for this workspace — everyone can read and post.
          </Text>
          <Spacer size={6} />

          {messages.length > 0 ? (
            <Card header={<CardHeader title="Messages" sub={`${messages.length} MESSAGES`} />}>
              <HairlineRowList>
                {messages.map((message) => {
                  const isOwn = message.senderAccountId === meId;
                  const isDeleted = message.deletedAt !== null;
                  const isEditing = editingId === message.id;
                  return (
                    <View
                      key={message.id}
                      testID={`message-row-${message.id}`}
                      style={[styles.row, isOwn && { backgroundColor: t.colors.bg.elevated }]}
                    >
                      <View style={styles.rowHeader}>
                        <Text variant="body" color={isOwn ? 'brand' : 'secondary'}>
                          {isOwn ? 'You' : shortId(message.senderAccountId)}
                        </Text>
                        <Spacer size={2} axis="horizontal" />
                        <Text variant="caption" color="tertiary">
                          {new Date(message.createdAt).toLocaleString()}
                          {message.editedAt ? ' · edited' : ''}
                        </Text>
                        {isOwn && !isDeleted ? (
                          <View style={styles.rowActions}>
                            <Pressable
                              onPress={() => startEdit(message)}
                              accessibilityRole="button"
                              accessibilityLabel="Edit message"
                              testID={`edit-message-${message.id}`}
                              style={styles.iconButton}
                            >
                              <Icon name="Pencil" size="sm" color="secondary" />
                            </Pressable>
                            <Pressable
                              onPress={() => deleteMessage.mutate(message.id)}
                              accessibilityRole="button"
                              accessibilityLabel="Delete message"
                              testID={`delete-message-${message.id}`}
                              style={styles.iconButton}
                            >
                              <Icon name="Trash2" size="sm" color="danger" />
                            </Pressable>
                          </View>
                        ) : null}
                      </View>
                      <Spacer size={1} />
                      {isEditing ? (
                        <View>
                          <TextInput
                            value={editDraft}
                            onChangeText={setEditDraft}
                            multiline
                            testID={`edit-input-${message.id}`}
                            style={[
                              styles.editInput,
                              {
                                color: t.colors.text.primary,
                                backgroundColor: t.colors.bg.card,
                                borderColor: t.colors.border.default,
                              },
                            ]}
                          />
                          <Spacer size={2} />
                          <View style={styles.editActions}>
                            <Button
                              label="Cancel"
                              variant="ghost"
                              size="sm"
                              onPress={cancelEdit}
                              testID={`cancel-edit-${message.id}`}
                            />
                            <Spacer size={2} axis="horizontal" />
                            <Button
                              label="Save"
                              variant="secondary"
                              size="sm"
                              loading={editMessage.isPending && editMessage.variables?.messageId === message.id}
                              onPress={() => saveEdit(message.id)}
                              testID={`save-edit-${message.id}`}
                            />
                          </View>
                        </View>
                      ) : (
                        <Text variant="body" color={isDeleted ? 'tertiary' : 'primary'}>
                          {isDeleted ? 'Message deleted' : message.body}
                        </Text>
                      )}
                    </View>
                  );
                })}
              </HairlineRowList>
            </Card>
          ) : !isLoading ? (
            <Card>
              <View style={styles.empty}>
                <Icon name="MessageCircle" size="lg" color="secondary" />
                <Spacer size={3} />
                <Text variant="body" color="secondary" style={{ textAlign: 'center' }}>
                  No messages yet. Say hello.
                </Text>
              </View>
            </Card>
          ) : null}

          <Spacer size={8} />
        </ScrollView>

        <View style={[styles.composer, { borderTopColor: t.colors.border.default }]}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder="Message the team…"
            placeholderTextColor={t.colors.text.tertiary}
            multiline
            testID="chat-message-input"
            style={[
              styles.composerInput,
              {
                color: t.colors.text.primary,
                backgroundColor: t.colors.bg.card,
                borderColor: t.colors.border.default,
              },
            ]}
          />
          <Spacer size={2} axis="horizontal" />
          <Button
            label="Send"
            size="sm"
            disabled={draft.trim().length === 0}
            loading={sendMessage.isPending}
            onPress={onSend}
            testID="send-message-button"
          />
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  row: { paddingHorizontal: 4, borderRadius: 8 },
  rowHeader: { flexDirection: 'row', alignItems: 'center' },
  rowActions: { flexDirection: 'row', marginLeft: 'auto', columnGap: 4 },
  iconButton: { padding: 6 },
  editInput: {
    minHeight: 40,
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 15,
  },
  editActions: { flexDirection: 'row', alignItems: 'center' },
  empty: { padding: 24, alignItems: 'center' },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingTop: 8,
    paddingBottom: 8,
    borderTopWidth: 1,
  },
  composerInput: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 15,
  },
});
