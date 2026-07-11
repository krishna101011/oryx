import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Icon,
  Pressable,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { AlertPreference, Automation } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';
import { EmptyState } from '../../../components/EmptyState';
import { FeatureGate } from '../../../components/FeatureGate';
import { ALERT_CATEGORIES, CATEGORY_COPY, FREQUENCY_COPY } from '../../settings/alertCategories';
import { type FeedRow, type FeedTone, toFeedRows } from '../feed';

/**
 * Automation Hub — Phase 6 Wave B. Tab names are the FROZEN doc's
 * (PHASE_6_ARCHITECTURE.md §6): Rules + Log.
 *
 * Rules: the per-category cadence currently in force — read-only reframe of
 * the same alert_preferences data; editing lives in Settings → Notification
 * preferences, deliberately not duplicated here.
 * Log: the transparency feed (GET /v1/automation-log) — every dispatcher
 * decision INCLUDING suppressions, plus sent digests, newest first.
 */
type HubTab = 'rules' | 'log';

export const AutomationHubScreen: React.FC = () => (
  <FeatureGate flag="ff_automation" name="Automation Hub" icon="Workflow">
    <HubContent />
  </FeatureGate>
);

const HubContent: React.FC = () => {
  const [tab, setTab] = useState<HubTab>('rules');

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        OPERATIONS
      </Text>
      <Spacer size={2} />
      <Text variant="display">Automation Hub</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        What fires, what gets held back, and why.
      </Text>
      <Spacer size={4} />

      <TabRow tab={tab} onChange={setTab} />
      <Spacer size={4} />

      <ScrollView showsVerticalScrollIndicator={false}>
        {tab === 'rules' ? <RulesTab /> : <LogTab />}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const TabRow: React.FC<{ tab: HubTab; onChange: (t: HubTab) => void }> = ({
  tab,
  onChange,
}) => {
  const t = useTheme();
  const tabs: { key: HubTab; label: string }[] = [
    { key: 'rules', label: 'Rules' },
    { key: 'log', label: 'Log' },
  ];
  return (
    <View style={[styles.tabRow, { backgroundColor: t.colors.bg.elevated, borderColor: t.colors.border.default }]}>
      {tabs.map(({ key, label }) => {
        const active = key === tab;
        return (
          <Pressable
            key={key}
            onPress={() => onChange(key)}
            style={[
              styles.tabBtn,
              active && {
                backgroundColor: t.colors.bg.card,
                borderColor: t.colors.border.strong,
                borderWidth: 1,
              },
            ]}
          >
            <Text variant="navLabel" color={active ? 'primary' : 'tertiary'}>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
};

// -------------------- Rules --------------------

const RulesTab: React.FC = () => {
  const prefs = useQuery<AlertPreference[]>({
    queryKey: ['alerts', 'preferences'],
    queryFn: () => apiClient().get<AlertPreference[]>('/activity/alerts/preferences'),
  });

  const frequencyOf = (category: string): string => {
    const row = (prefs.data ?? []).find(
      (p) => p.type === category && p.channel === 'in_app',
    );
    return row ? FREQUENCY_COPY[row.frequency].label : '—';
  };

  return (
    <>
      {ALERT_CATEGORIES.map((category) => (
        <React.Fragment key={category}>
          <RuleCard
            label={CATEGORY_COPY[category].label}
            description={CATEGORY_COPY[category].description}
            frequency={frequencyOf(category)}
            active={frequencyOf(category) !== FREQUENCY_COPY.off.label}
          />
          <Spacer size={2} />
        </React.Fragment>
      ))}
      <Spacer size={2} />
      <Text variant="caption" color="tertiary">
        Edit these in Settings → Notification preferences.
      </Text>
    </>
  );
};

const RuleCard: React.FC<{
  label: string;
  description: string;
  frequency: string;
  active: boolean;
}> = ({ label, description, frequency, active }) => {
  const t = useTheme();
  return (
    <Card variant="default">
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text variant="body">{label}</Text>
          <Spacer size={1} />
          <Text variant="bodySm" color="secondary">
            {description}
          </Text>
        </View>
        <View
          style={[
            styles.freqBadge,
            {
              backgroundColor: active
                ? t.colors.semantic.positiveSurface
                : t.colors.bg.elevated,
            },
          ]}
        >
          <Text
            variant="label"
            style={{
              color: active ? t.colors.semantic.positiveText : t.colors.text.tertiary,
            }}
          >
            {frequency}
          </Text>
        </View>
      </View>
    </Card>
  );
};

// -------------------- Log --------------------

const LogTab: React.FC = () => {
  const log = useQuery<Automation.AutomationLogResponse>({
    queryKey: ['automation', 'log'],
    queryFn: () => apiClient().get<Automation.AutomationLogResponse>('/automation-log'),
  });

  const rows = toFeedRows(log.data?.entries ?? []);

  if (rows.length === 0) {
    return (
      <EmptyState
        title="Nothing in the log yet"
        description="Every delivered, digested, or suppressed notification will be recorded here."
      />
    );
  }

  return (
    <>
      {rows.map((row) => (
        <React.Fragment key={row.id}>
          <LogCard row={row} />
          <Spacer size={2} />
        </React.Fragment>
      ))}
    </>
  );
};

const LogCard: React.FC<{ row: FeedRow }> = ({ row }) => {
  const t = useTheme();
  const [expanded, setExpanded] = useState(false);
  const toneColor: Record<FeedTone, string> = {
    positive: t.colors.semantic.positiveText,
    warn: t.colors.semantic.warning,
    danger: t.colors.semantic.danger,
    neutral: t.colors.text.tertiary,
  };
  return (
    <Pressable
      onPress={() => setExpanded((v) => !v)}
      accessibilityRole="button"
      accessibilityLabel={`${row.title} — ${expanded ? 'hide' : 'show'} details`}
    >
      <Card variant="default">
        <View style={styles.row}>
          <View style={[styles.iconWrap, { backgroundColor: t.colors.bg.elevated }]}>
            <Icon name={row.icon} size="sm" color="secondary" />
          </View>
          <View style={{ flex: 1 }}>
            <Text variant="body">{row.title}</Text>
            {row.subtitle ? (
              <>
                <Spacer size={1} />
                <Text variant="bodySm" color="secondary">
                  {row.subtitle}
                </Text>
              </>
            ) : null}
            <Spacer size={1} />
            <Text variant="caption" color="tertiary">
              {new Date(row.createdAt).toLocaleString()}
            </Text>
          </View>
          <View style={[styles.toneDot, { backgroundColor: toneColor[row.tone] }]} />
          <View style={styles.expandIcon}>
            <Icon name={expanded ? 'ChevronUp' : 'ChevronDown'} size="sm" color="tertiary" />
          </View>
        </View>
        {expanded ? (
          <View
            style={[styles.detailBlock, { borderTopColor: t.colors.border.default }]}
          >
            {row.detail.map((line) => (
              <View key={line.label} style={styles.detailLine}>
                <Text variant="caption" color="tertiary">
                  {line.label}
                </Text>
                <Text variant="bodySm" color="secondary" style={{ flexShrink: 1, textAlign: 'right' }}>
                  {line.value}
                </Text>
              </View>
            ))}
          </View>
        ) : null}
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  tabRow: {
    flexDirection: 'row',
    borderRadius: 10,
    borderWidth: 1,
    padding: 3,
    alignSelf: 'flex-start',
  },
  tabBtn: {
    paddingVertical: 6,
    paddingHorizontal: 18,
    borderRadius: 8,
  },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  freqBadge: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 8,
    marginLeft: 12,
  },
  toneDot: { width: 8, height: 8, borderRadius: 4, marginTop: 8, marginLeft: 8 },
  expandIcon: { marginTop: 4, marginLeft: 8 },
  detailBlock: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    rowGap: 6,
  },
  detailLine: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    columnGap: 12,
  },
});
