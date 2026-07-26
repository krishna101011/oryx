import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ChangeMemberRoleRequest,
  CreateInviteRequest,
  InviteRole,
  WorkspaceInvite,
  WorkspaceInvitesListResponse,
  WorkspaceMemberSummary,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

const MEMBERS_KEY = ['workspace', 'members'];
const INVITES_KEY = ['workspace', 'invites'];
const ACTIVITY_KEY = ['workspace', 'activity'];

export function useMembers() {
  return useQuery<WorkspaceMemberSummary[]>({
    queryKey: MEMBERS_KEY,
    queryFn: () => apiClient().get<WorkspaceMemberSummary[]>('/workspaces/members'),
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) =>
      apiClient().delete<{ removed: boolean }>(`/workspaces/members/${accountId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MEMBERS_KEY });
      void queryClient.invalidateQueries({ queryKey: ACTIVITY_KEY });
    },
  });
}

// Role-change wave: closes the real remove+reinvite-to-change-access gap.
// Same invalidation shape as useRemoveMember — a role change also produces a
// new real activity event.
export function useChangeMemberRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, role }: { accountId: string; role: InviteRole }) =>
      apiClient().patch<WorkspaceMemberSummary, ChangeMemberRoleRequest>(
        `/workspaces/members/${accountId}`,
        { role },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: MEMBERS_KEY });
      void queryClient.invalidateQueries({ queryKey: ACTIVITY_KEY });
    },
  });
}

// GET /workspaces/invites is workspace.manage-gated (see workspaces/router.py)
// — callers pass `enabled: canManage` so an editor/reader viewing Members
// never fires a request that would 403.
export function usePendingInvites(enabled: boolean) {
  return useQuery<WorkspaceInvitesListResponse>({
    queryKey: INVITES_KEY,
    queryFn: () => apiClient().get<WorkspaceInvitesListResponse>('/workspaces/invites'),
    enabled,
  });
}

export function useCreateInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateInviteRequest) =>
      apiClient().post<WorkspaceInvite, CreateInviteRequest>('/workspaces/invites', body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: INVITES_KEY });
      void queryClient.invalidateQueries({ queryKey: ACTIVITY_KEY });
    },
  });
}

export function useRevokeInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) =>
      apiClient().post<{ revoked: boolean }>(`/workspaces/invites/${inviteId}/revoke`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: INVITES_KEY }),
  });
}
