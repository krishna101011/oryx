import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Spacer, Text, Screen } from '@oryx/design-system';
import type {
  NotificationFrequency,
  UpdatePreferencesRequest,
} from '@oryx/shared-types';
import { useMe } from '../../../hooks/useMe';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { apiClient } from '../../../lib/api/client';

export const AlertsSettingsScreen: React.FC = () => {
  const me = useMe();
  const queryClient = useQueryClient();
  const current = me.data?.preferences.notificationFrequency ?? 'daily';
  const [frequency, setFrequency] = useState<NotificationFrequency>(current);

  const mutation = useMutation({
    mutationFn: (body: UpdatePreferencesRequest) =>
      apiClient().patch('/preferences', body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['me'] }),
  });

  const pick = async (f: NotificationFrequency) => {
    setFrequency(f);
    await mutation.mutateAsync({ notificationFrequency: f });
  };

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="display">Alerts</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        How often we tell you about new activity.
      </Text>
      <Spacer size={6} />

      <ChoiceTile
        label="Off"
        description="Only critical security alerts."
        selected={frequency === 'off'}
        onPress={() => pick('off')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Instant"
        description="Push for high-priority items."
        selected={frequency === 'instant'}
        onPress={() => pick('instant')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Daily digest"
        selected={frequency === 'daily'}
        onPress={() => pick('daily')}
      />
      <Spacer size={2} />
      <ChoiceTile
        label="Weekly digest"
        selected={frequency === 'weekly'}
        onPress={() => pick('weekly')}
      />
    </Screen>
  );
};
