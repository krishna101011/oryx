import React, { useMemo, useState } from 'react';
import { ScrollView } from 'react-native';
import { Screen, Spacer, Text } from '@oryx/design-system';
import {
  useIntakeSources,
  useSourceCatalog,
  useToggleCatalogSource,
} from '../../intake/hooks/useIntakeSources';
import { CatalogSourcePicker } from '../../intake/components/CatalogSourcePicker';
import { buildCatalogActivationMap, resolveToggleAction } from '../../intake/catalogPicker';

export const TrustedSourcesScreen: React.FC = () => {
  const catalog = useSourceCatalog();
  const sources = useIntakeSources();
  const toggle = useToggleCatalogSource();
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const activationMap = useMemo(
    () => buildCatalogActivationMap(sources.data ?? []),
    [sources.data],
  );

  const onToggle = (key: string) => {
    setPendingKey(key);
    toggle.mutate(resolveToggleAction(key, activationMap), {
      onSettled: () => setPendingKey(null),
    });
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Trusted sources</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Toggle the real sources that feed your intelligence pipeline.
        </Text>
        <Spacer size={6} />
        <CatalogSourcePicker
          catalog={catalog.data ?? []}
          activationMap={activationMap}
          onToggle={onToggle}
          pendingKeys={pendingKey ? new Set([pendingKey]) : undefined}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
