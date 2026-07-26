import { useQuery } from '@tanstack/react-query';
import type { WorkspaceActivityListResponse } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

const ACTIVITY_KEY = ['workspace', 'activity'];

// GET /workspaces/activity is member-visible (no workspace.manage gate, see
// services/workspaces/router.py's list_activity) — every role that can see
// the member list can see who was invited/joined/removed.
export function useTeamActivity() {
  return useQuery<WorkspaceActivityListResponse>({
    queryKey: ACTIVITY_KEY,
    queryFn: () => apiClient().get<WorkspaceActivityListResponse>('/workspaces/activity'),
  });
}
