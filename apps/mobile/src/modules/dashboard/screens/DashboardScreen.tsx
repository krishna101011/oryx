import React from 'react';
import { View, StyleSheet } from 'react-native';
import {
  Card,
  Screen,
  Spacer,
  Text,
  Divider,
  useTheme,
} from '@oryx/design-system';
import { useIntakeStatus } from '../../intake/hooks/useIntakeSources';
import { sourcesStatValue } from '../stats';

/**
 * Phase 1 dashboard — not placeholder, real shell.
 * Renders the brand mark and a structured layout so the home tab feels
 * like the eventual product.
 *
 * SOURCES is real (GET /intake/status). VERIFIED and DRAFTS are still the
 * Phase 1 hardcoded zeros — wiring them is flagged, not silently done, in
 * the 2026-07-11 report (they need an owner decision on which number
 * "VERIFIED" even means).
 */
export const DashboardScreen: React.FC = () => {
  const t = useTheme();
  const intakeStatus = useIntakeStatus();
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
        <Text variant="h2">Today</Text>
        <Spacer size={4} />
        <Text variant="body" color="secondary">
          Nothing to surface yet. Connect a source to begin.
        </Text>
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
              0
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
              0
            </Text>
          </View>
        </View>
      </Card>

      {__DEV__ && (
        <>
          <Spacer size={6} />
          <Divider variant="subtle" />
          <Spacer size={4} />
          <Text variant="caption" color="tertiary">
            PHASE 1 — FOUNDATION
          </Text>
        </>
      )}
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  col: { flex: 1 },
  separator: { width: 1, marginHorizontal: 16 },
});
