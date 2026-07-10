import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Pressable,
  Screen,
  Spacer,
  Spark,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { Analytics } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';
import { EmptyState } from '../../../components/EmptyState';
import { FeatureGate } from '../../../components/FeatureGate';
import { BarSeries } from '../components/BarSeries';
import {
  CHART_WINDOW_DAYS,
  type Series,
  type Trend,
  buildFunnel,
  buildKpis,
  formatDuration,
  formatSuccessRate,
  formatTrend,
  funnelIsEmpty,
  hasAnyData,
  padDailySeries,
} from '../presenter';

/**
 * Analytics — Phase 7 Wave B. Follows the AutomationHubScreen shape
 * (FeatureGate → Screen → header → TabRow → ScrollView) with three tabs:
 *
 * Overview: KPI cards + daily charts over Wave A's rollups.
 * Research: the §3.3 verification/research funnel — where activity
 * concentrates, in pipeline order.
 * Publishing: §3.4's delivery view ONLY — success rate + time-to-publish.
 * No engagement/view number exists anywhere because no real signal does.
 *
 * Everything reads analytics_rollups_daily via GET /analytics/rollups except
 * time-to-publish (GET /analytics/publishing, computed on request). Wave A
 * only just shipped, so a workspace with no rollup rows is the NORMAL state:
 * each tab renders a "still gathering" state instead of a wall of zeros.
 */
type AnalyticsTab = 'overview' | 'research' | 'publishing';

/** Overview time-series: the funnel's entry, core, and exit metrics. */
const CHART_DEFS: { key: string; label: string }[] = [
  { key: 'intake_items_received', label: 'Items ingested' },
  { key: 'claims_verified', label: 'Claims verified' },
  { key: 'drafts_published', label: 'Drafts published' },
];

const todayUtc = (): string => new Date().toISOString().slice(0, 10);

export const AnalyticsHomeScreen: React.FC = () => (
  <FeatureGate flag="ff_analytics" name="Analytics" icon="BarChart3">
    <AnalyticsContent />
  </FeatureGate>
);

const AnalyticsContent: React.FC = () => {
  const [tab, setTab] = useState<AnalyticsTab>('overview');

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        OPERATIONS
      </Text>
      <Spacer size={2} />
      <Text variant="display">Analytics</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        What the pipeline did, measured — nothing invented.
      </Text>
      <Spacer size={4} />

      <TabRow tab={tab} onChange={setTab} />
      <Spacer size={4} />

      <ScrollView showsVerticalScrollIndicator={false}>
        {tab === 'overview' ? <OverviewTab /> : null}
        {tab === 'research' ? <ResearchTab /> : null}
        {tab === 'publishing' ? <PublishingTab /> : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const TabRow: React.FC<{ tab: AnalyticsTab; onChange: (t: AnalyticsTab) => void }> = ({
  tab,
  onChange,
}) => {
  const t = useTheme();
  const tabs: { key: AnalyticsTab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'research', label: 'Research' },
    { key: 'publishing', label: 'Publishing' },
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

// -------------------- shared data --------------------

const useRollups = () =>
  useQuery<Analytics.AnalyticsRollupsResponse>({
    queryKey: ['analytics', 'rollups'],
    queryFn: () =>
      apiClient().get<Analytics.AnalyticsRollupsResponse>('/analytics/rollups'),
  });

const GATHERING_TITLE = 'Still gathering data';
const GATHERING_BODY =
  'Metrics appear here as ORYX processes activity — ingestion, verification, and publishing all feed this view.';

// -------------------- Overview --------------------

const OverviewTab: React.FC = () => {
  const rollups = useRollups();
  if (!rollups.data) return null;

  const series: Series = rollups.data.series;
  if (!hasAnyData(series)) {
    return <EmptyState title={GATHERING_TITLE} description={GATHERING_BODY} />;
  }

  const today = todayUtc();
  const kpis = buildKpis(series, today);
  const charts = CHART_DEFS.filter(({ key }) => (series[key] ?? []).length > 0);

  return (
    <>
      <View style={styles.kpiGrid}>
        {kpis.map((kpi) => (
          <Card key={kpi.key} variant="default" style={styles.kpiCard}>
            <Text variant="caption" color="tertiary">
              {kpi.label.toUpperCase()}
            </Text>
            <Spacer size={1} />
            <Text variant="h1">{kpi.value === null ? '—' : String(kpi.value)}</Text>
            <Spacer size={1} />
            <Text variant="caption" color="tertiary">
              last 7 days
            </Text>
            <TrendLine trend={kpi.trend} />
            <Spacer size={2} />
            <Spark data={kpi.spark} width={96} height={18} />
          </Card>
        ))}
      </View>
      <Spacer size={4} />
      {charts.map(({ key, label }) => (
        <React.Fragment key={key}>
          <Card variant="default">
            <Text variant="body">{label}</Text>
            <Spacer size={1} />
            <Text variant="caption" color="tertiary">
              daily · last {CHART_WINDOW_DAYS} days
            </Text>
            <Spacer size={2} />
            <BarSeries data={padDailySeries(series, key, today, CHART_WINDOW_DAYS)} />
          </Card>
          <Spacer size={2} />
        </React.Fragment>
      ))}
      {charts.length === 0 ? (
        <Text variant="caption" color="tertiary">
          Daily charts appear as pipeline activity accrues.
        </Text>
      ) : null}
    </>
  );
};

/**
 * Wave C trend row on a KPI card. Renders nothing when the metric is absent
 * (the card's em-dash value already says "not yet measured" — a trend line
 * would dress absence up as a fact). Tones follow the automation feed's
 * FeedTone → semantic color convention.
 */
const TrendLine: React.FC<{ trend: Trend | null }> = ({ trend }) => {
  const t = useTheme();
  const display = formatTrend(trend);
  if (display === null) return null;
  const color = {
    positive: t.colors.semantic.positiveText,
    danger: t.colors.semantic.danger,
    neutral: t.colors.text.tertiary,
  }[display.tone];
  return (
    <>
      <Spacer size={1} />
      <Text variant="caption" style={{ color }}>
        {display.text}
      </Text>
    </>
  );
};

// -------------------- Research --------------------

const ResearchTab: React.FC = () => {
  const t = useTheme();
  const rollups = useRollups();
  if (!rollups.data) return null;

  const stages = buildFunnel(rollups.data.series, todayUtc(), CHART_WINDOW_DAYS);
  if (funnelIsEmpty(stages)) {
    return (
      <EmptyState
        title="No research activity yet"
        description="The verification funnel fills in as claims are extracted, verified, and assembled into research packets."
      />
    );
  }

  return (
    <Card variant="default">
      <Text variant="body">Verification & research funnel</Text>
      <Spacer size={1} />
      <Text variant="caption" color="tertiary">
        totals · last {CHART_WINDOW_DAYS} days
      </Text>
      <Spacer size={3} />
      {stages.map((stage) => (
        <View key={stage.key} style={styles.funnelRow}>
          <View style={styles.funnelLabel}>
            <Text variant="bodySm" color="secondary">
              {stage.label}
            </Text>
          </View>
          <View style={[styles.funnelTrack, { backgroundColor: t.colors.bg.elevated }]}>
            <View
              style={[
                styles.funnelFill,
                {
                  backgroundColor: t.colors.accent.plum,
                  // Non-zero stages keep a visible sliver even when dwarfed.
                  width: `${stage.total > 0 ? Math.max(stage.ratio * 100, 3) : 0}%`,
                },
              ]}
            />
          </View>
          <View style={styles.funnelCount}>
            <Text variant="bodySm">{String(stage.total)}</Text>
          </View>
        </View>
      ))}
    </Card>
  );
};

// -------------------- Publishing --------------------

const PublishingTab: React.FC = () => {
  const publishing = useQuery<Analytics.AnalyticsPublishingResponse>({
    queryKey: ['analytics', 'publishing'],
    queryFn: () =>
      apiClient().get<Analytics.AnalyticsPublishingResponse>('/analytics/publishing'),
  });
  if (!publishing.data) return null;

  const { success, timeToPublish } = publishing.data;
  const rate = formatSuccessRate(success);
  const average = formatDuration(timeToPublish.averageSeconds);
  const median = formatDuration(timeToPublish.medianSeconds);

  if (rate === null && timeToPublish.sampleSize === 0) {
    return (
      <EmptyState
        title="Nothing published yet"
        description="Delivery success and time-to-publish appear once drafts start going out."
      />
    );
  }

  return (
    <>
      <Card variant="default">
        <Text variant="caption" color="tertiary">
          DELIVERY SUCCESS · LAST 30 DAYS
        </Text>
        <Spacer size={2} />
        <Text variant="h1">{rate ?? '—'}</Text>
        <Spacer size={1} />
        <Text variant="bodySm" color="secondary">
          {success.published} delivered · {success.failed} failed
        </Text>
      </Card>
      <Spacer size={2} />
      <Card variant="default">
        <Text variant="caption" color="tertiary">
          TIME TO PUBLISH
        </Text>
        <Spacer size={2} />
        {timeToPublish.sampleSize === 0 ? (
          <Text variant="bodySm" color="secondary">
            Appears once the first draft is delivered.
          </Text>
        ) : (
          <>
            <Text variant="h1">{median ?? '—'}</Text>
            <Spacer size={1} />
            <Text variant="bodySm" color="secondary">
              median from draft to delivery · average {average} · last{' '}
              {timeToPublish.sampleSize} publications
            </Text>
          </>
        )}
      </Card>
    </>
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
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  kpiCard: {
    flexGrow: 1,
    flexBasis: '47%',
  },
  funnelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  funnelLabel: { width: 140 },
  funnelTrack: {
    flex: 1,
    height: 10,
    borderRadius: 5,
    overflow: 'hidden',
    marginHorizontal: 8,
  },
  funnelFill: {
    height: '100%',
    borderRadius: 5,
  },
  funnelCount: { width: 40, alignItems: 'flex-end' },
});
