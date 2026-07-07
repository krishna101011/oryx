import React from 'react';
import { ScrollView } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Screen, Spacer, Text } from '@oryx/design-system';
import type { AlertPreference, NotificationFrequency, UpdateAlertPreferenceRequest } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { ALERT_CATEGORIES, type AlertCategory, CATEGORY_COPY, FREQUENCY_COPY } from '../alertCategories';

const FREQUENCIES: NotificationFrequency[] = ['off', 'instant', 'daily', 'weekly'];

/**
 * Notification Preferences — Phase 6 Wave B.
 *
 * Per-category frequency against the REAL alert_preferences model
 * (GET/PUT /activity/alerts/preferences, channel 'in_app' — the only channel
 * that delivers before Wave C). Replaces the Phase-2 placeholder that wrote
 * the single global preferences.notificationFrequency; that field remains for
 * onboarding but this screen now edits the per-category grid the dispatcher
 * and DigestWorker actually read.
 */
export const AlertsSettingsScreen: React.FC = () => {
  const queryClient = useQueryClient();

  const prefs = useQuery<AlertPreference[]>({
    queryKey: ['alerts', 'preferences'],
    queryFn: () => apiClient().get<AlertPreference[]>('/activity/alerts/preferences'),
  });

  const update = useMutation({
    mutationFn: ({ category, frequency }: { category: AlertCategory; frequency: NotificationFrequency }) =>
      apiClient().put<AlertPreference, UpdateAlertPreferenceRequest>(
        `/activity/alerts/preferences/${category}/in_app`,
        { frequency },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts', 'preferences'] }),
  });

  const frequencyOf = (category: AlertCategory): NotificationFrequency => {
    const row = (prefs.data ?? []).find(
      (p) => p.type === category && p.channel === 'in_app',
    );
    // The server backfills the full resolved grid, so a missing row only
    // happens while the query is in flight — mirror the server default.
    return row?.frequency ?? 'instant';
  };

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Notification preferences</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          How often each kind of activity reaches you. Daily digests arrive at
          8:00 in your timezone; weekly on Monday mornings.
        </Text>

        {ALERT_CATEGORIES.map((category) => (
          <React.Fragment key={category}>
            <Spacer size={6} />
            <Text variant="caption" color="tertiary">
              {CATEGORY_COPY[category].label.toUpperCase()}
            </Text>
            <Spacer size={1} />
            <Text variant="bodySm" color="secondary">
              {CATEGORY_COPY[category].description}
            </Text>
            <Spacer size={2} />
            {FREQUENCIES.map((frequency) => (
              <React.Fragment key={frequency}>
                <ChoiceTile
                  label={FREQUENCY_COPY[frequency].label}
                  description={FREQUENCY_COPY[frequency].description}
                  selected={frequencyOf(category) === frequency}
                  onPress={() => update.mutate({ category, frequency })}
                />
                <Spacer size={2} />
              </React.Fragment>
            ))}
          </React.Fragment>
        ))}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
