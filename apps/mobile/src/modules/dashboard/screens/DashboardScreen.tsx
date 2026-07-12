import React from 'react';
import { View, StyleSheet } from 'react-native';
import {
  Card,
  Icon,
  Pressable,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import { useMe } from '../../../hooks/useMe';
import { navigateSettingsScreen } from '../../../navigation/navigationRef';
import { useIntakeStatus, useRecentIntakeItems } from '../../intake/hooks/useIntakeSources';
import {
  draftsStatValue,
  sourcesStatValue,
  todayPanelState,
  todayRowTarget,
  verifiedStatValue,
} from '../stats';

function timeLabel(receivedAt: string): string {
  const d = new Date(receivedAt);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Command Center. "Today" shows the real most-recent ingested items
 * (GET /intake/items/recent — headline + source), not the generic
 * activity_inbox notification rows; the Activity tab owns those.
 *
 * All three stats are real: SOURCES (GET /intake/status), VERIFIED
 * (/me verification.verifiedCount) and DRAFTS (/me content.draftCount).
 */
export const DashboardScreen: React.FC = () => {
  const t = useTheme();
  const me = useMe();
  const intakeStatus = useIntakeStatus();
  const recentItems = useRecentIntakeItems();
  const today = todayPanelState(recentItems.data);
  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        ORYX
      </Text>
      <Spacer size={2} />
      <Text variant="display">Good morning.</Text>
      <Spacer size={1} />
      <Text variant="bodySm" color="secondary">
        Your intelligence operating system.
      </Text>

      <Spacer size={8} />

      <Card variant="default">
        <Text variant="cardTitle" color="secondary">
          Today
        </Text>
        {today.kind === 'empty' && (
          <>
            <Spacer size={4} />
            <Text variant="body" color="secondary">
              Nothing to surface yet. Connect a source to begin.
            </Text>
          </>
        )}
        {today.kind === 'list' &&
          today.rows.map((row, idx) => {
            // Same destination as Activity rows and search results — the one
            // registered IntakeItemDetail screen, resolved by todayRowTarget.
            const target = todayRowTarget(row);
            return (
              <Pressable
                key={row.id}
                onPress={() => navigateSettingsScreen(target.screen, target.params)}
                accessibilityRole="button"
                accessibilityLabel={row.headline}
              >
                <Spacer size={idx === 0 ? 4 : 3} />
                <View style={styles.todayRow}>
                  <View style={{ flex: 1 }}>
                    <Text variant="body" numberOfLines={2}>
                      {row.headline}
                    </Text>
                    <Spacer size={1} />
                    <Text variant="caption" color="tertiary">
                      {row.source}
                      {timeLabel(row.receivedAt) ? `  ·  ${timeLabel(row.receivedAt)}` : ''}
                    </Text>
                  </View>
                  <View style={styles.chevron}>
                    <Icon name="ChevronRight" size="sm" color="tertiary" />
                  </View>
                </View>
              </Pressable>
            );
          })}
      </Card>

      <Spacer size={4} />

      <Card variant="elevated">
        <View style={styles.row}>
          <View style={styles.col}>
            <Text variant="caption" color="tertiary">
              SOURCES
            </Text>
            <Spacer size={1} />
            <Text variant="mono" color="primary">
              {sourcesStatValue(intakeStatus.data)}
            </Text>
          </View>
          <View
            style={[
              styles.separator,
              { backgroundColor: t.colors.border.subtle },
            ]}
          />
          <View style={styles.col}>
            <Text variant="caption" color="tertiary">
              VERIFIED
            </Text>
            <Spacer size={1} />
            <Text variant="mono" color="primary">
              {verifiedStatValue(me.data)}
            </Text>
          </View>
          <View
            style={[
              styles.separator,
              { backgroundColor: t.colors.border.subtle },
            ]}
          />
          <View style={styles.col}>
            <Text variant="caption" color="tertiary">
              DRAFTS
            </Text>
            <Spacer size={1} />
            <Text variant="mono" color="primary">
              {draftsStatValue(me.data)}
            </Text>
          </View>
        </View>
      </Card>

    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  col: { flex: 1 },
  separator: { width: 1, marginHorizontal: 16 },
  todayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  chevron: { marginTop: 4, marginLeft: 8 },
});
