import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, View } from 'react-native';
import { type RouteProp, useNavigation, useRoute } from '@react-navigation/native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Icon, Screen, Spacer, Text, type IconName } from '@oryx/design-system';
import type { AcceptInviteResult, WorkspaceInvite } from '@oryx/shared-types';
import type { SettingsStackParamList } from '../../../navigation/types';
import { apiClient } from '../../../lib/api/client';
import { isApiError } from '../../../lib/errors';
import { useAppDispatch, useAppSelector } from '../../../store';
import { switchWorkspace } from '../../../store/thunks/auth';

function title(value: string): string {
  return value.length === 0 ? value : value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * Deep-link target for the invite email. GET /workspaces/invites/{token}
 * returns 200 with the real invite fields even once it's resolved (expired/
 * revoked/accepted) — only a genuinely unknown token 404s (see
 * services/workspaces/router.py's view_invite). Every real state that
 * implies is rendered here explicitly; none of them is a guess.
 */
export const AcceptInviteScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'AcceptInvite'>>();
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const queryClient = useQueryClient();
  const refreshToken = useAppSelector((s) => s.auth.refreshToken);
  const { token } = route.params;

  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);

  const invite = useQuery<WorkspaceInvite>({
    queryKey: ['invite', token],
    queryFn: () => apiClient().get<WorkspaceInvite>(`/workspaces/invites/${token}`),
    retry: false,
  });

  const accept = useMutation({
    mutationFn: () => apiClient().post<AcceptInviteResult>(`/workspaces/invites/${token}/accept`),
    onError: (e) => setAcceptError(isApiError(e) ? e.message : 'Could not accept this invite.'),
    onSuccess: () => {
      // A brand new real membership exists now — the sidebar switcher's
      // ['workspaces'] list (and ['me']) would otherwise stay stale until
      // some unrelated refetch happened to fire.
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      void queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });

  const onSwitchNow = async () => {
    if (!accept.data) return;
    setSwitchError(null);
    // A real, pre-existing web-platform gap (not fixed here — it's the same
    // constraint /auth/refresh already has): the refresh token is never
    // cookied, only the access token is, so it only lives in Redux for the
    // tab that just completed a live signin/signup. A page reload — which is
    // exactly what opening this deep link from a real invite email does —
    // leaves it null. Surface that honestly rather than silently no-op.
    if (!refreshToken) {
      setSwitchError('Switching needs a fresh sign-in in this browser tab — please sign out and sign back in, then try again.');
      return;
    }
    setSwitching(true);
    try {
      await dispatch(switchWorkspace(accept.data.workspaceId, refreshToken));
      navigation.navigate('SettingsHome' as never);
    } catch (e) {
      setSwitchError(isApiError(e) ? e.message : 'Could not switch to this workspace.');
    } finally {
      setSwitching(false);
    }
  };

  const renderState = (icon: IconName, danger: boolean, heading: string, body: string) => (
    <Card>
      <View style={{ padding: 16, alignItems: 'center' }}>
        <Icon name={icon} size="lg" color={danger ? 'danger' : 'secondary'} />
        <Spacer size={3} />
        <Text variant="h2">{heading}</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary" style={{ textAlign: 'center' }}>
          {body}
        </Text>
      </View>
    </Card>
  );

  let body: React.ReactNode;

  if (invite.isLoading) {
    body = (
      <View style={{ padding: 24, alignItems: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  } else if (invite.error) {
    const notFound = isApiError(invite.error) && invite.error.code === 'INVITE_NOT_FOUND';
    body = renderState(
      'XCircle',
      true,
      notFound ? 'Invite not found' : 'Something went wrong',
      notFound
        ? "This invite link isn't valid — it may have been mistyped or already removed."
        : 'Could not load this invite. Please try again.',
    );
  } else if (invite.data?.revokedAt) {
    body = renderState(
      'Ban',
      true,
      'Invite revoked',
      'Whoever sent this invite has revoked it. Ask them to send a new one if you still want to join.',
    );
  } else if (invite.data?.acceptedAt) {
    body = renderState(
      'CheckCircle2',
      false,
      'Already accepted',
      'This invite has already been accepted.',
    );
  } else if (invite.data && new Date(invite.data.expiresAt).getTime() < Date.now()) {
    body = renderState(
      'Clock',
      true,
      'Invite expired',
      'This invite is past its expiry date. Ask whoever sent it to send a new one.',
    );
  } else if (accept.isSuccess && accept.data) {
    body = (
      <Card>
        <View style={{ padding: 16, alignItems: 'center' }}>
          <Icon name="CheckCircle2" size="lg" color="secondary" />
          <Spacer size={3} />
          <Text variant="h2">You're in</Text>
          <Spacer size={2} />
          <Text variant="body" color="secondary" style={{ textAlign: 'center' }}>
            You joined as {title(accept.data.role)}.
          </Text>
          {switchError ? (
            <>
              <Spacer size={2} />
              <Text variant="caption" color="danger">{switchError}</Text>
            </>
          ) : null}
          <Spacer size={4} />
          <Button
            label="Switch to this workspace now"
            fullWidth
            loading={switching}
            onPress={onSwitchNow}
            testID="switch-to-joined-workspace"
          />
          <Spacer size={2} />
          <Button
            label="Stay here for now"
            variant="ghost"
            fullWidth
            onPress={() => navigation.navigate('SettingsHome' as never)}
          />
        </View>
      </Card>
    );
  } else if (invite.data) {
    body = (
      <Card>
        <View style={{ padding: 16, alignItems: 'center' }}>
          <Icon name="Mail" size="lg" color="secondary" />
          <Spacer size={3} />
          <Text variant="h2">You've been invited</Text>
          <Spacer size={2} />
          <Text variant="body" color="secondary" style={{ textAlign: 'center' }}>
            {invite.data.invitedEmail} is invited as {title(invite.data.role)}.
          </Text>
          {acceptError ? (
            <>
              <Spacer size={2} />
              <Text variant="caption" color="danger">{acceptError}</Text>
            </>
          ) : null}
          <Spacer size={4} />
          <Button
            label="Accept invite"
            fullWidth
            loading={accept.isPending}
            onPress={() => accept.mutate()}
            testID="accept-invite-button"
          />
        </View>
      </Card>
    );
  }

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Workspace invite</Text>
        <Spacer size={6} />
        {body}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
