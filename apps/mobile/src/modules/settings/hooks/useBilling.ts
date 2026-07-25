import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  PlansResponse,
  SubscribeRequest,
  SubscribeResult,
  SubscriptionSummary,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export function usePlans() {
  return useQuery<PlansResponse>({
    queryKey: ['billing', 'plans'],
    queryFn: () => apiClient().get<PlansResponse>('/billing/plans'),
    // The real catalog changes rarely (a pricing decision, not live data) —
    // no reason to refetch on every focus like useMe does.
    staleTime: 5 * 60 * 1000,
  });
}

export function useSubscriptionSummary() {
  return useQuery<SubscriptionSummary>({
    queryKey: ['billing', 'subscription'],
    queryFn: () => apiClient().get<SubscriptionSummary>('/billing/subscription'),
  });
}

export function useSubscribe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SubscribeRequest) =>
      apiClient().post<SubscribeResult, SubscribeRequest>('/billing/subscribe', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['billing', 'subscription'] }),
  });
}
