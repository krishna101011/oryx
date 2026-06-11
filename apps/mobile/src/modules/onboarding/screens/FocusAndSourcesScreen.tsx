import React, { useMemo, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import { Spacer, Text } from '@anant/design-system';
import type {
  Focus,
  OnboardingStepRequest,
  SourceCatalogEntry,
} from '@anant/shared-types';
import { OnboardingShell } from '../components/OnboardingShell';
import { ChoiceTile } from '../components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';

export const FocusAndSourcesScreen: React.FC = () => {
  const navigation = useNavigation();
  const [focus, setFocus] = useState<Focus>('both');
  const [loading, setLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());

  const catalog = useQuery<SourceCatalogEntry[]>({
    queryKey: ['sources', 'catalog'],
    queryFn: () => apiClient().get<SourceCatalogEntry[]>('/sources/catalog'),
  });

  const filtered = useMemo(() => {
    const entries = catalog.data ?? [];
    return entries.filter(
      (s) => focus === 'both' || s.focus === 'both' || s.focus === focus,
    );
  }, [catalog.data, focus]);

  const toggleSource = (key: string) => {
    setSelectedSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const onContinue = async () => {
    setLoading(true);
    try {
      const body: OnboardingStepRequest = {
        step: 'focus_sources',
        focus,
        enabledSourceKeys: Array.from(selectedSources),
      };
      await apiClient().post('/onboarding/step', body);
      navigation.navigate('NotificationsAndPermissions' as never);
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingShell
      stepIndex={1}
      title="What do you follow?"
      subtitle="Pick a focus and confirm your trusted sources."
      onContinue={onContinue}
      loading={loading}
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
        {filtered.map((s) => (
          <View key={s.key}>
            <ChoiceTile
              label={s.name}
              description={`Editorial confidence: ${s.editorialConfidence}`}
              selected={selectedSources.has(s.key)}
              onPress={() => toggleSource(s.key)}
            />
            <Spacer size={2} />
          </View>
        ))}
      </ScrollView>
    </OnboardingShell>
  );
};
