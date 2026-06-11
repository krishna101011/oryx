import { useInfiniteQuery } from '@tanstack/react-query';
import type { IntakeSourceAuditEntry } from '@anant/shared-types';
import { intakeApi } from '../api/intake';

/** Cursor-paginated audit timeline for one source (CR-9 contract). */
export function useSourceAudit(sourceId: string) {
  return useInfiniteQuery({
    queryKey: ['intake', 'audit', sourceId],
    queryFn: async ({ pageParam }) =>
      intakeApi.audit(sourceId, pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.meta?.pagination?.nextCursor ?? null,
    select: (data) => ({
      pages: data.pages,
      pageParams: data.pageParams,
      entries: data.pages.flatMap(
        (p) => p.data as IntakeSourceAuditEntry[],
      ),
    }),
  });
}
