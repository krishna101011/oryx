import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Spacer, Text } from '@anant/design-system';
import type {
  ContentStyle,
  OnboardingStepRequest,
  VerificationStrictness,
} from '@anant/shared-types';
import { OnboardingShell } from '../components/OnboardingShell';
import { ChoiceTile } from '../components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';

export const StyleAndStrictnessScreen: React.FC = () => {
  const queryClient = useQueryClient();
  const [style, setStyle] = useState<ContentStyle>('balanced');
  const [strictness, setStrictness] = useState<VerificationStrictness>('balanced');
  const [loading, setLoading] = useState(false);

  const onContinue = async () => {
    setLoading(true);
    try {
      const body: OnboardingStepRequest = {
        step: 'style_strictness',
        contentStyle: style,
        verificationStrictness: strictness,
      };
      await apiClient().post('/onboarding/step', body);
      // Re-pull /me so RootNavigator switches to Tabs.
      await queryClient.invalidateQueries({ queryKey: ['me'] });
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingShell
      stepIndex={3}
      title="Your reading style"
      subtitle="Choose how content reads and how strict verification should be."
      onContinue={onContinue}
      continueLabel="Finish"
      loading={loading}
    >
      <Text variant="caption" color="tertiary">
        CONTENT STYLE
      </Text>
      <Spacer size={2} />
      <ChoiceTile
        label="Concise"
        description="Headlines and the essentials only."
        selected={style === 'concise'}
        onPress={() => setStyle('concise')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Balanced"
        description="A summary with the key context."
        selected={style === 'balanced'}
        onPress={() => setStyle('balanced')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Detailed"
        description="Full analysis with citations."
        selected={style === 'detailed'}
        onPress={() => setStyle('detailed')}
      />

      <Spacer size={6} />
      <Text variant="caption" color="tertiary">
        VERIFICATION STRICTNESS
      </Text>
      <Spacer size={2} />
      <ChoiceTile
        label="Loose"
        description="Show everything; flag unverified inline."
        selected={strictness === 'loose'}
        onPress={() => setStrictness('loose')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Balanced"
        description="Verified by default; unverified behind a tap."
        selected={strictness === 'balanced'}
        onPress={() => setStrictness('balanced')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Strict"
        description="Hide unverified from primary surfaces."
        selected={strictness === 'strict'}
        onPress={() => setStrictness('strict')}
      />
    </OnboardingShell>
  );
};
