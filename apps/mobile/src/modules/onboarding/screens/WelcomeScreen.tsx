import React, { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import type { OnboardingStepRequest } from '@anant/shared-types';
import { OnboardingShell } from '../components/OnboardingShell';
import { apiClient } from '../../../lib/api/client';

export const WelcomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(false);

  const onContinue = async () => {
    setLoading(true);
    try {
      await apiClient().post<unknown, OnboardingStepRequest>('/onboarding/step', {
        step: 'welcome',
      });
      navigation.navigate('FocusAndSources' as never);
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingShell
      stepIndex={0}
      title="Welcome to Anant."
      subtitle="Your intelligence operating system. Let's get you set up in under a minute."
      onContinue={onContinue}
      continueLabel="Get started"
      loading={loading}
    >
      {null}
    </OnboardingShell>
  );
};
