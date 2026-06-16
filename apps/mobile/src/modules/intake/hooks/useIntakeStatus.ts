import { useQuery } from '@tanstack/react-query';
import type { IntakeStatusSummary } from '@oryx/shared-types';
import { intakeApi } from '../api/intake';

/** Per-workspace health rollup for the intake dashboard. */
export function useIntakeStatus() {
  return useQuery<IntakeStatusSummary>({
    queryKey: ['intake', 'status'],
    queryFn: () => intakeApi.status(),
    refetchInterval: 60 * 1000, // operational surface: keep it fresh
  });
}
