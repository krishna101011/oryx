import React from 'react';
import { ScrollView } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Screen, Spacer, Text } from '@oryx/design-system';
import type { AlertPreference, NotificationFrequency, UpdateAlertPreferenceRequest } from '@oryx/shared-types';
import { useMe } from '../../../hooks/useMe';
import { apiClient } from '../../../lib/api/client';
import { usePushRegistration } from '../../../lib/push/usePushRegistration';
import { ChoiceTile } from '../../onboarding/components/ChoiceTile';
import { ALERT_CATEGORIES, type AlertCategory, CATEGORY_COPY, FREQUENCY_COPY } from '../alertCategories';
import {
  QUIET_HOURS_PRESETS,
  type QuietHoursPreset,
  buildQuietHours,
  deviceTimeZone,
  presetKeyFor,
} from '../quietHours';

const FREQUENCIES: NotificationFrequency[] = ['off', 'instant', 'daily', 'weekly'];

/**
 * Notification Preferences — Phase 6 Wave B (+ Wave C push).
 *
 * Per-category frequency against the REAL alert_preferences model
 * (GET/PUT /activity/alerts/preferences, channel 'in_app'). Wave C adds:
 * - push-token registration on mount (usePushRegistration — this screen is
 *   where the user is thinking about notifications, so the OS permission
 *   prompt appears in context);
 * - the deferred quiet-hours control: a preset range written to every
 *   category's push-channel row, evaluated by the dispatcher's push step.
 */
export const AlertsSettingsScreen: React.FC = () => {
  const queryClient = useQueryClient();
  const me = useMe();
  const pushEnabled = me.data?.flags?.ff_push_delivery ?? false;
  usePushRegistration(pushEnabled);

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

  const pushFrequencyOf = (category: AlertCategory): NotificationFrequency => {
    const row = (prefs.data ?? []).find(
      (p) => p.type === category && p.channel === 'push',
    );
    return row?.frequency ?? 'instant';
  };

  // Quiet hours apply to the PUSH channel, uniformly across categories: one
  // PUT per category, each preserving that row's own frequency (the endpoint
  // resets an omitted frequency to 'instant', so it must be echoed back).
  const updateQuietHours = useMutation({
    mutationFn: (preset: QuietHoursPreset) => {
      const quietHours = buildQuietHours(preset, deviceTimeZone());
      return Promise.all(
        ALERT_CATEGORIES.map((category) =>
          apiClient().put<AlertPreference, UpdateAlertPreferenceRequest>(
            `/activity/alerts/preferences/${category}/push`,
            { frequency: pushFrequencyOf(category), quietHours },
          ),
        ),
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts', 'preferences'] }),
  });

  // The presets write one uniform window, so any push row is representative;
  // prefer one that actually holds a value.
  const quietHoursValue =
    (prefs.data ?? []).find((p) => p.channel === 'push' && p.quietHours != null)
      ?.quietHours ?? null;
  const selectedPreset = presetKeyFor(quietHoursValue);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Notification preferences</Text>
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

        {pushEnabled ? (
          <>
            <Spacer size={6} />
            <Text variant="caption" color="tertiary">
              QUIET HOURS
            </Text>
            <Spacer size={1} />
            <Text variant="bodySm" color="secondary">
              Pushes pause during this window, in your local time. The in-app
              feed is never held back.
            </Text>
            <Spacer size={2} />
            {QUIET_HOURS_PRESETS.map((preset) => (
              <React.Fragment key={preset.key}>
                <ChoiceTile
                  label={preset.label}
                  description={preset.description}
                  selected={selectedPreset === preset.key}
                  onPress={() => updateQuietHours.mutate(preset)}
                />
                <Spacer size={2} />
              </React.Fragment>
            ))}
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};
