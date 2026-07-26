import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Screen,
  Spacer,
  Text,
} from '@oryx/design-system';
import type { InviteRole } from '@oryx/shared-types';
import { isApiError } from '../../../lib/errors';
import { useMe } from '../../../hooks/useMe';
import { AuthFormField } from '../../auth/components/AuthFormField';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { describeActivityEvent } from '../activityCopy';
import { useTeamActivity } from '../hooks/useTeamActivity';
import {
  useCreateInvite,
  useMembers,
  usePendingInvites,
  useRemoveMember,
  useRevokeInvite,
} from '../hooks/useWorkspaceMembers';

const ROLE_COPY: Record<InviteRole, { label: string; description: string }> = {
  admin: { label: 'Admin', description: 'Can manage members, invites, and workspace settings' },
  editor: { label: 'Editor', description: 'Can create and edit research and content' },
  reader: { label: 'Reader', description: 'Read-only access' },
};
const ROLE_OPTIONS: InviteRole[] = ['admin', 'editor', 'reader'];

// The landing screen's own preview only needs a glance, not the full history
// the dedicated Activity screen shows.
const RECENT_ACTIVITY_PREVIEW_COUNT = 3;

function title(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1);
}

function shortId(id: string): string {
  return id.length <= 8 ? id : `${id.slice(0, 8)}…`;
}

/**
 * Team section landing screen (moved verbatim from Settings > Members, plus
 * a real recent-activity preview — Team promotion wave, 2026-07-26): the
 * member list, invite form, pending invites, and remove/revoke controls are
 * unchanged from the prior Settings sub-screen; only the surrounding nav
 * placement changed (see navigation/TeamStack.tsx, webNav.ts).
 */
export const TeamHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const me = useMe();
  // Only owner/admin carry workspace.manage (CAPABILITIES["admin"|"owner"] —
  // see core/dependencies.py) — editor/reader get a read-only member list,
  // matching what the backend would actually let them do.
  const canManage = me.data?.workspace.role === 'owner' || me.data?.workspace.role === 'admin';

  const members = useMembers();
  const removeMember = useRemoveMember();
  const pendingInvites = usePendingInvites(canManage);
  const createInvite = useCreateInvite();
  const revokeInvite = useRevokeInvite();
  const activity = useTeamActivity();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<InviteRole>('editor');
  const [inviteError, setInviteError] = useState<string | null>(null);

  const onSendInvite = () => {
    setInviteError(null);
    createInvite.mutate(
      { email: email.trim(), role },
      {
        onSuccess: () => setEmail(''),
        onError: (e) => setInviteError(isApiError(e) ? e.message : 'Could not send invite.'),
      },
    );
  };

  const invites = pendingInvites.data?.invites ?? [];
  const recentEvents = (activity.data?.events ?? []).slice(0, RECENT_ACTIVITY_PREVIEW_COUNT);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Team</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Who has access to this workspace.
        </Text>
        <Spacer size={6} />

        <Card
          header={
            <CardHeader
              title="Members"
              sub={`${(members.data ?? []).length} ACTIVE`}
            />
          }
        >
          <HairlineRowList>
            {(members.data ?? []).map((m) => {
              const isSelf = m.accountId === me.data?.account.id;
              const removable = canManage && m.role !== 'owner' && !isSelf;
              return (
                <View key={m.accountId} style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <Text variant="body">
                      {isSelf ? 'You' : shortId(m.accountId)}
                    </Text>
                    <Spacer size={1} />
                    <Text variant="caption" color="tertiary">
                      {title(m.role)} · Joined {new Date(m.joinedAt).toLocaleDateString()}
                    </Text>
                  </View>
                  {removable ? (
                    <Button
                      label="Remove"
                      variant="ghost"
                      size="sm"
                      loading={removeMember.isPending && removeMember.variables === m.accountId}
                      onPress={() => removeMember.mutate(m.accountId)}
                      testID={`remove-member-${m.accountId}`}
                    />
                  ) : null}
                </View>
              );
            })}
          </HairlineRowList>
        </Card>

        {canManage ? (
          <>
            <Spacer size={6} />
            <Card header={<CardHeader title="Invite a member" />}>
              <View style={styles.inviteForm}>
                <AuthFormField
                  label="Email"
                  value={email}
                  onChangeText={setEmail}
                  keyboardType="email-address"
                  errorText={inviteError}
                  testID="invite-email-input"
                />
                <Spacer size={4} />
                <Text variant="caption" color="tertiary">
                  ROLE
                </Text>
                <Spacer size={2} />
                {ROLE_OPTIONS.map((r) => (
                  <React.Fragment key={r}>
                    <ChoiceTile
                      label={ROLE_COPY[r].label}
                      description={ROLE_COPY[r].description}
                      selected={role === r}
                      onPress={() => setRole(r)}
                    />
                    <Spacer size={2} />
                  </React.Fragment>
                ))}
                <Spacer size={2} />
                <Button
                  label="Send invite"
                  fullWidth
                  disabled={email.trim().length === 0}
                  loading={createInvite.isPending}
                  onPress={onSendInvite}
                  testID="send-invite-button"
                />
              </View>
            </Card>
          </>
        ) : (
          <>
            <Spacer size={4} />
            <View style={styles.footnote}>
              <Icon name="ShieldCheck" size="sm" color="secondary" />
              <Text variant="caption" color="secondary">
                Only workspace owners and admins can invite or remove members.
              </Text>
            </View>
          </>
        )}

        {canManage && invites.length > 0 ? (
          <>
            <Spacer size={6} />
            <Card header={<CardHeader title="Pending invites" sub={`${invites.length} PENDING`} />}>
              <HairlineRowList>
                {invites.map((invite) => {
                  const isExpired = new Date(invite.expiresAt).getTime() < Date.now();
                  return (
                    <View key={invite.id} style={styles.row}>
                      <View style={{ flex: 1 }}>
                        <Text variant="body">{invite.invitedEmail}</Text>
                        <Spacer size={1} />
                        <Text variant="caption" color={isExpired ? 'danger' : 'tertiary'}>
                          {title(invite.role)} ·{' '}
                          {isExpired
                            ? 'Expired'
                            : `Expires ${new Date(invite.expiresAt).toLocaleDateString()}`}
                        </Text>
                      </View>
                      <Button
                        label="Revoke"
                        variant="ghost"
                        size="sm"
                        loading={revokeInvite.isPending && revokeInvite.variables === invite.id}
                        onPress={() => revokeInvite.mutate(invite.id)}
                        testID={`revoke-invite-${invite.id}`}
                      />
                    </View>
                  );
                })}
              </HairlineRowList>
            </Card>
          </>
        ) : null}

        {recentEvents.length > 0 ? (
          <>
            <Spacer size={6} />
            <Card header={<CardHeader title="Recent activity" />}>
              <HairlineRowList>
                {recentEvents.map((event) => {
                  const copy = describeActivityEvent(event, me.data?.account.id);
                  return (
                    <View key={event.id} style={styles.row}>
                      <Icon name={copy.icon} size="sm" color="secondary" />
                      <Spacer size={3} axis="horizontal" />
                      <View style={{ flex: 1 }}>
                        <Text variant="body">{copy.text}</Text>
                        <Spacer size={1} />
                        <Text variant="caption" color="tertiary">
                          {new Date(event.createdAt).toLocaleString()}
                        </Text>
                      </View>
                    </View>
                  );
                })}
              </HairlineRowList>
              <Spacer size={2} />
              <View style={styles.viewAllRow}>
                <Button
                  label="View all activity"
                  variant="ghost"
                  size="sm"
                  onPress={() => navigation.navigate('TeamActivity' as never)}
                  testID="view-all-activity-button"
                />
              </View>
            </Card>
          </>
        ) : null}

        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  inviteForm: { padding: 12 },
  footnote: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 4,
  },
  viewAllRow: { alignItems: 'flex-end', paddingHorizontal: 4 },
});
