import { useCallback, useEffect, useState } from 'react';
import type { ContentTemplate } from '@oryx/shared-types';
import { templatesApi } from '../api/templates';

interface UseTemplatesResult {
  templates: ContentTemplate[];
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useTemplates(format?: string): UseTemplatesResult {
  const [templates, setTemplates] = useState<ContentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await templatesApi.list(format);
      setTemplates(res.data ?? []);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [format]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { templates, loading, error, refetch: fetch };
}
