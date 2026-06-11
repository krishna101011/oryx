import React, { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { Spacer, Text } from '@anant/design-system';
import type {
  NotificationFrequency,
  OnboardingStepRequest,
} from '@anant/shared-types';
import { OnboardingShell } from '../components/OnboardingShell';
import { ChoiceTile } from '../components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';

export const NotificationsAndPermissionsScreen: React.FC = () => {
  const navigation = useNavigation();
  const [freq, setFreq] = useState<NotificationFrequency>('daily');
  const [loading, setLoading] = useState(false);

  const onContinue = async () => {
    setLoading(true);
    try {
      const body: OnboardingStepRequest = {
        step: 'notifications_permissions',
        notificationFrequency: freq,
      };
      await apiClient().post('/onboarding/step', body);
      navigation.navigate('StyleAndStrictness' as never);
    } finally {
      setLoading(false);
    }
  };

  return (
    <OnboardingShell
      stepIndex={2}
      title="When should we tell you?"
      subtitle="You can change this at any time in Settings → Alerts."
      onContinue={onContinue}
      loading={loading}
    >
      <Text variant="caption" color="tertiary">
        FREQUENCY
      </Text>
      <Spacer size={2} />
      <ChoiceTile
        label="Off"
        description="Only critical security alerts."
        selected={freq === 'off'}
        onPress={() => setFreq('off')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Daily digest"
        description="One curated summary every morning."
        selected={freq === 'daily'}
        onPress={() => setFreq('daily')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Weekly digest"
        description="A roundup every Monday."
        selected={freq === 'weekly'}
        onPress={() => setFreq('weekly')}
      />
    </OnboardingShell>
  );
};
