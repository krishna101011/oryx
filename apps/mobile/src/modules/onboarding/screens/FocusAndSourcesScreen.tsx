import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Spacer, Text } from '@oryx/design-system';
import type { Focus, OnboardingStepRequest } from '@oryx/shared-types';
import { OnboardingShell } from '../components/OnboardingShell';
import { ChoiceTile } from '../components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';
import {
  useIntakeSources,
  useSourceCatalog,
  useToggleCatalogSource,
} from '../../intake/hooks/useIntakeSources';
import { CatalogSourcePicker } from '../../intake/components/CatalogSourcePicker';
import {
  buildCatalogActivationMap,
  filterCatalogByFocus,
  keysMissingActivation,
  resolveToggleAction,
} from '../../intake/catalogPicker';

export const FocusAndSourcesScreen: React.FC = () => {
  const navigation = useNavigation();
  const [focus, setFocus] = useState<Focus>('both');
  const [loading, setLoading] = useState(false);
  const [pendingKey, setPendingKey] = useState<string | null>(null);

  const catalog = useSourceCatalog();
  const sources = useIntakeSources();
  const toggle = useToggleCatalogSource();

  const activationMap = useMemo(
    () => buildCatalogActivationMap(sources.data ?? []),
    [sources.data],
  );

  const dataReady = catalog.data !== undefined && sources.data !== undefined;
  const missingKeys = dataReady ? keysMissingActivation(catalog.data!, activationMap) : [];

  // Fresh-signup default: every real catalog entry is pre-checked with a
  // REAL intake_sources row, not just a visually-checked tile — same
  // "toggle = real activation" contract as TrustedSourcesScreen. The
  // provisioned ref guards against firing a second create for a key whose
  // first create is still in flight (activationMap only reflects a key once
  // its row lands and the query cache refetches); it does NOT re-enable a
  // row the user already turned off, since it only ever targets keys with
  // no existing row at all.
  const provisioned = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!dataReady) return;
    for (const key of missingKeys) {
      if (provisioned.current.has(key)) continue;
      provisioned.current.add(key);
      toggle.mutate({ kind: 'create', catalogKey: key });
    }
  }, [dataReady, missingKeys.join(',')]);

  const provisioning = !dataReady || missingKeys.length > 0;

  const onToggle = (key: string) => {
    setPendingKey(key);
    toggle.mutate(resolveToggleAction(key, activationMap), {
      onSettled: () => setPendingKey(null),
    });
  };

  const onContinue = async () => {
    setLoading(true);
    try {
      const body: OnboardingStepRequest = { step: 'focus_sources', focus };
      await apiClient().post('/onboarding/step', body);
      navigation.navigate('NotificationsAndPermissions' as never);
    } finally {
      setLoading(false);
    }
  };

  const visibleCatalog = filterCatalogByFocus(catalog.data ?? [], focus);

  return (
    <OnboardingShell
      stepIndex={1}
      title="What do you follow?"
      subtitle="Pick a focus and confirm your trusted sources."
      onContinue={onContinue}
      loading={loading || provisioning}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        <Text variant="caption" color="tertiary">
          FOCUS
        </Text>
        <Spacer size={2} />
        <ChoiceTile
          label="Markets"
          description="Equities, macro, rates, commodities."
          selected={focus === 'markets'}
          onPress={() => setFocus('markets')}
        />
        <Spacer size={2} />
        <ChoiceTile
          label="Crypto"
          description="On-chain, exchanges, tokens, DeFi."
          selected={focus === 'crypto'}
          onPress={() => setFocus('crypto')}
        />
        <Spacer size={2} />
        <ChoiceTile
          label="Both"
          description="Full coverage across markets and crypto."
          selected={focus === 'both'}
          onPress={() => setFocus('both')}
        />

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          TRUSTED SOURCES
        </Text>
        <Spacer size={2} />
        <CatalogSourcePicker
          catalog={visibleCatalog}
          activationMap={activationMap}
          onToggle={onToggle}
          pendingKeys={pendingKey ? new Set([pendingKey]) : undefined}
          isLoading={catalog.isLoading}
        />
      </ScrollView>
    </OnboardingShell>
  );
};
