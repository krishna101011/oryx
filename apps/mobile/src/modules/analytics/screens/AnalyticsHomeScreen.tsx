import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Pressable,
  Screen,
  Skeleton,
  SkeletonTile,
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
  formatFunnelDrop,
  formatSuccessRate,
  formatTrend,
  funnelIsEmpty,
  funnelSummary,
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
      <Text variant="pageTitle">Analytics</Text>
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

/**
 * Reference .tab-row / .tab scale (styles.css:262-264) — the exact fix
 * shipped for Automation Hub in the AH-4 wave, ported verbatim: radius-5
 * container, 2px padding + 2px gap, radius-3 tabs at 3×10 padding, 11px text
 * (bodySm, the closest variant at 11.5), active = --elev-2 fill, and 12px
 * vertical hitSlop keeping the touch target ≥44px at the ~22px drawn height.
 */
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
    <View
      style={[
        styles.tabRow,
        {
          backgroundColor: t.colors.bg.elevated,
          borderColor: t.colors.border.default,
          borderRadius: t.radius.md,
        },
      ]}
    >
      {tabs.map(({ key, label }) => {
        const active = key === tab;
        return (
          <Pressable
            key={key}
            onPress={() => onChange(key)}
            hitSlop={{ top: 12, bottom: 12 }}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={label}
            style={[
              styles.tabBtn,
              { borderRadius: t.radius.sm },
              active && { backgroundColor: t.colors.bg.elevated2 },
            ]}
          >
            <Text variant="bodySm" color={active ? 'primary' : 'tertiary'}>
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
  if (rollups.isLoading || !rollups.data) {
    return (
      <>
        <View style={styles.kpiGrid}>
          {/* Real KPI tile anatomy (label + kpiVal + "last 7 days" caption +
              trend + Spark), see SkeletonTile's own hasSparkline doc. */}
          <SkeletonTile hasSparkline style={styles.kpiCard} />
          <SkeletonTile hasSparkline style={styles.kpiCard} />
          <SkeletonTile hasSparkline style={styles.kpiCard} />
        </View>
        <Spacer size={4} />
        {/* Daily chart cards aren't in the catalogued row/tile shape family
            (recon scoped SkeletonRow/SkeletonTile to KPI tiles and funnel
            rows) — a generic block is the honest placeholder here. */}
        <Card variant="default">
          <Skeleton width="40%" height={11} radius={2} />
          <Spacer size={1} />
          <Skeleton width="55%" height={9} radius={2} />
          <Spacer size={2} />
          <Skeleton width="100%" height={80} radius={4} />
        </Card>
      </>
    );
  }

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
            <Text variant="kpiVal">{kpi.value === null ? '—' : String(kpi.value)}</Text>
            <Spacer size={1} />
            <Text variant="caption" color="tertiary">
              last 7 days
            </Text>
            <TrendLine trend={kpi.trend} />
            <Spacer size={2} />
            {/* Reference .kpi .micro (styles.css:372): full tile width × 28. */}
            <Spark data={kpi.spark} fullWidth height={28} />
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
  if (rollups.isLoading || !rollups.data) {
    return (
      <Card variant="default">
        <Skeleton width="60%" height={11} radius={2} />
        <Spacer size={1} />
        <Skeleton width="45%" height={9} radius={2} />
        <Spacer size={3} />
        <SkeletonFunnelRow />
        <SkeletonFunnelRow />
        <SkeletonFunnelRow />
        <SkeletonFunnelRow />
      </Card>
    );
  }

  const stages = buildFunnel(rollups.data.series, todayUtc(), CHART_WINDOW_DAYS);
  const summary = funnelSummary(stages);
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
      {stages.map((stage) => {
        const drop = formatFunnelDrop(stage.drop);
        return (
          <View key={stage.key} style={styles.funnelRow}>
            {/* Reference funnel row head (analytics.jsx:68-72): label, mono
                count right-aligned, then the drop column — which only exists
                for stages a real predecessor feeds (see FUNNEL_DEFS). */}
            <View style={styles.funnelHead}>
              <Text variant="bodySm" color="secondary" style={{ flex: 1 }}>
                {stage.label}
              </Text>
              <Text variant="mono">{String(stage.total)}</Text>
              {drop ? (
                <Text
                  variant="caption"
                  style={[
                    styles.funnelDrop,
                    {
                      color:
                        drop.tone === 'danger'
                          ? t.colors.semantic.danger
                          : t.colors.text.tertiary,
                    },
                  ]}
                >
                  {drop.text}
                </Text>
              ) : null}
            </View>
            <View
              style={[
                styles.funnelTrack,
                {
                  backgroundColor: t.colors.bg.elevated,
                  borderRadius: t.gensparkRadius.r2,
                },
              ]}
            >
              <View
                style={[
                  styles.funnelFill,
                  {
                    backgroundColor: t.colors.accent.plum,
                    borderRadius: t.gensparkRadius.r2,
                    // Non-zero stages keep a visible sliver even when dwarfed.
                    width: `${stage.total > 0 ? Math.max(stage.ratio * 100, 3) : 0}%`,
                  },
                ]}
              />
            </View>
          </View>
        );
      })}
      {summary ? (
        <View style={[styles.funnelSummary, { borderTopColor: t.colors.border.default }]}>
          <Text variant="caption" color="tertiary">
            {summary.label}
          </Text>
          <Text variant="mono" style={{ color: t.colors.semantic.positiveText }}>
            {summary.text}
          </Text>
        </View>
      ) : null}
    </Card>
  );
};

/**
 * Bespoke — single consumer (Research tab has no analog elsewhere in the
 * app; recon confirmed the funnel row doesn't fit the shared SkeletonRow
 * family). Mirrors the real funnel row: label + mono count on the head
 * line, then the full-width track — height 18 is an EXACT match to
 * `styles.funnelTrack` below, not an approximation, since the track's real
 * height is fixed regardless of data.
 */
const SkeletonFunnelRow: React.FC = () => {
  const t = useTheme();
  return (
    <View style={styles.funnelRow}>
      <View style={styles.funnelHead}>
        <Skeleton width="50%" height={9} radius={2} />
        <Skeleton width={24} height={9} radius={2} />
      </View>
      <Skeleton width="100%" height={18} radius={t.gensparkRadius.r2} />
    </View>
  );
};

// -------------------- Publishing --------------------

const PublishingTab: React.FC = () => {
  const publishing = useQuery<Analytics.AnalyticsPublishingResponse>({
    queryKey: ['analytics', 'publishing'],
    queryFn: () =>
      apiClient().get<Analytics.AnalyticsPublishingResponse>('/analytics/publishing'),
  });
  if (publishing.isLoading || !publishing.data) {
    return (
      <>
        {/* Both real Publishing cards share the KPI-tile anatomy (caption
            label + kpiVal + a descriptive detail line), just full-width
            instead of the 47%-basis grid — SkeletonTile's detailWidth
            covers the extra line neither Dashboard's nor Automation's
            plain tiles have. */}
        <SkeletonTile detailWidth="70%" />
        <Spacer size={2} />
        <SkeletonTile detailWidth="85%" />
      </>
    );
  }

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
        <Text variant="kpiVal">{rate ?? '—'}</Text>
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
            <Text variant="kpiVal">{median ?? '—'}</Text>
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
  // .tab-row { gap:2px; border:1px; padding:2px } — radius via t.radius.md.
  tabRow: {
    flexDirection: 'row',
    columnGap: 2,
    borderWidth: 1,
    padding: 2,
    alignSelf: 'flex-start',
  },
  // .tab-row .tab { padding:3px 10px } — radius via t.radius.sm.
  tabBtn: {
    paddingVertical: 3,
    paddingHorizontal: 10,
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
  // Reference funnel row (analytics.jsx:67-76): stacked head line + full-width
  // 18px track; radii applied inline via t.gensparkRadius.r2.
  funnelRow: { marginBottom: 8 },
  funnelHead: {
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    marginBottom: 3,
  },
  // The reference's fixed drop column: width 56, right-aligned.
  funnelDrop: { width: 56, textAlign: 'right' },
  funnelTrack: {
    height: 18,
    overflow: 'hidden',
  },
  funnelFill: {
    height: '100%',
  },
  // Reference summary row (analytics.jsx:79): top border + spaced pair.
  funnelSummary: {
    marginTop: 4,
    paddingTop: 8,
    borderTopWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
});
