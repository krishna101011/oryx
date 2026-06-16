import React, { useMemo } from 'react';
import { ScrollView } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Screen, Spacer, Text } from '@oryx/design-system';
import type {
  SourceCatalogEntry,
  UpdateWorkspaceSourceRequest,
  WorkspaceSource,
} from '@oryx/shared-types';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';

export const TrustedSourcesScreen: React.FC = () => {
  const queryClient = useQueryClient();

  const catalog = useQuery<SourceCatalogEntry[]>({
    queryKey: ['sources', 'catalog'],
    queryFn: () => apiClient().get<SourceCatalogEntry[]>('/sources/catalog'),
  });
  const enabled = useQuery<WorkspaceSource[]>({
    queryKey: ['sources', 'workspace'],
    queryFn: () => apiClient().get<WorkspaceSource[]>('/sources/workspace'),
  });

  const enabledKeys = useMemo(
    () => new Set((enabled.data ?? []).filter((s) => s.enabled).map((s) => s.sourceKey)),
    [enabled.data],
  );

  const toggle = useMutation({
    mutationFn: ({ key, on }: { key: string; on: boolean }) =>
      apiClient().put<WorkspaceSource, UpdateWorkspaceSourceRequest>(
        `/sources/workspace/${key}`,
        { enabled: on },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources', 'workspace'] }),
  });

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Trusted sources</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Toggle the sources that feed your intelligence pipeline.
        </Text>
        <Spacer size={6} />
        {(catalog.data ?? []).map((s) => (
          <React.Fragment key={s.key}>
            <ChoiceTile
              label={s.name}
              description={`Editorial confidence: ${s.editorialConfidence}`}
              selected={enabledKeys.has(s.key)}
              onPress={() =>
                toggle.mutate({ key: s.key, on: !enabledKeys.has(s.key) })
              }
            />
            <Spacer size={2} />
          </React.Fragment>
        ))}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
