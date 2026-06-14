import { useQuery } from '@tanstack/react-query';
import type {
  Claim,
  EvidenceWithLink,
  IntelligenceObject,
} from '@anant/shared-types';
import { type ObjectFilters, intelligenceApi } from '../api/intelligence';

export function useIntelligenceObject(objectId: string) {
  return useQuery<IntelligenceObject>({
    queryKey: ['intelligence', 'object', objectId],
    queryFn: () => intelligenceApi.getObject(objectId),
  });
}

export function useIntelligenceObjects(filters: ObjectFilters) {
  return useQuery<IntelligenceObject[]>({
    queryKey: ['intelligence', 'objects', filters],
    queryFn: async () => (await intelligenceApi.listObjects(filters)).data,
  });
}

export function useClaim(claimId: string) {
  return useQuery<Claim>({
    queryKey: ['claims', claimId],
    queryFn: () => intelligenceApi.getClaim(claimId),
  });
}

export function useClaimEvidence(claimId: string) {
  return useQuery<EvidenceWithLink[]>({
    queryKey: ['evidence', claimId],
    queryFn: async () => (await intelligenceApi.listEvidence(claimId)).data,
  });
}
