import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ReadinessResult,
  ResearchPacket,
  ResearchWorkspace,
} from '@oryx/shared-types';
import {
  type ResearchItemView,
  type WorkspaceDetail,
  researchApi,
} from '../api/research';

export function useResearchWorkspaces() {
  return useQuery<ResearchWorkspace[]>({
    queryKey: ['research', 'workspaces'],
    queryFn: async () => (await researchApi.listWorkspaces()).data,
  });
}

export function useResearchWorkspace(id: string) {
  return useQuery<WorkspaceDetail>({
    queryKey: ['research', 'workspace', id],
    queryFn: () => researchApi.getWorkspace(id),
  });
}

export function useWorkspaceItems(id: string) {
  return useQuery<ResearchItemView[]>({
    queryKey: ['research', 'workspace', id, 'items'],
    queryFn: async () => (await researchApi.listItems(id)).data,
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string | null }) =>
      researchApi.createWorkspace(body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['research', 'workspaces'] }),
  });
}

export function useAddItem(rwsId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { intelligence_object_id: string; note?: string | null }) =>
      researchApi.addItem(rwsId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['research', 'workspace', rwsId, 'items'] }),
  });
}

export function usePackets() {
  return useQuery<ResearchPacket[]>({
    queryKey: ['research', 'packets'],
    queryFn: async () => (await researchApi.listPacketsForWorkspace()).data,
  });
}

export function usePacket(id: string) {
  return useQuery<ResearchPacket>({
    queryKey: ['research', 'packet', id],
    queryFn: () => researchApi.getPacket(id),
  });
}

export function usePacketReadiness(id: string) {
  return useQuery<ReadinessResult>({
    queryKey: ['research', 'packet', id, 'readiness'],
    queryFn: () => researchApi.getReadiness(id),
  });
}

export function useCreatePacket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      research_workspace_id: string;
      name: string;
      intelligence_object_ids: string[];
    }) => researchApi.createPacket(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['research', 'packets'] }),
  });
}

export function useMarkReady(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => researchApi.markReady(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['research', 'packet', id] });
      qc.invalidateQueries({ queryKey: ['research', 'packet', id, 'readiness'] });
      qc.invalidateQueries({ queryKey: ['research', 'packets'] });
    },
  });
}
