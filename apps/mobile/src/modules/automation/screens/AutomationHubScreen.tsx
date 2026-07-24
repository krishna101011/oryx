import React, { useState } from 'react';
import { ScrollView, StyleSheet, type TextStyle, View, type ViewStyle } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  type Gx,
  HairlineRowList,
  Icon,
  Pressable,
  Screen,
  Spacer,
  Text,
  useGx,
  useTheme,
} from '@oryx/design-system';
import type { AlertPreference, Automation } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';
import { EmptyState } from '../../../components/EmptyState';
import { FeatureGate } from '../../../components/FeatureGate';
import { ALERT_CATEGORIES, CATEGORY_COPY, FREQUENCY_COPY } from '../../settings/alertCategories';
import { type FeedRow, type FeedTone, logTimestamp, outcomeChipLabel, toFeedRows } from '../feed';
import { hubKpis } from '../stats';

/**
 * Automation Hub — Phase 6 Wave B, row anatomy rebuilt in the
 * design-foundation wave (AH-1..AH-4, 2026-07-16). Tab names are the FROZEN
 * doc's (PHASE_6_ARCHITECTURE.md §6): Rules + Log.
 *
 * Rules: the per-category cadence currently in force — read-only reframe of
 * the same alert_preferences data; editing lives in Settings → Notification
 * preferences, deliberately not duplicated here. The reference's per-rule
 * toggle, fires count, and last-fired columns have NO real backing (no edit
 * action here; no per-category aggregates — the event→category mapping lives
 * only in the backend dispatcher CATALOG), so none of them are rendered.
 * Log: the transparency feed (GET /v1/automation-log) — every dispatcher
 * decision INCLUDING suppressions, plus sent digests, newest first. Rows
 * expand on press to show Channel/Trigger/Reason (wired in the "four
 * decorative surfaces" wave — behavior preserved by expandOnPress.test.tsx).
 */
type HubTab = 'rules' | 'log';

export const AutomationHubScreen: React.FC = () => (
  <FeatureGate flag="ff_automation" name="Automation Hub" icon="Workflow">
    <HubContent />
  </FeatureGate>
);

const HubContent: React.FC = () => {
  const [tab, setTab] = useState<HubTab>('rules');
  const prefs = useQuery<AlertPreference[]>({
    queryKey: ['alerts', 'preferences'],
    queryFn: () => apiClient().get<AlertPreference[]>('/activity/alerts/preferences'),
  });
  const log = useQuery<Automation.AutomationLogResponse>({
    queryKey: ['automation', 'log'],
    queryFn: () => apiClient().get<Automation.AutomationLogResponse>('/automation-log'),
  });

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        OPERATIONS
      </Text>
      <Spacer size={2} />
      <Text variant="pageTitle">Automation Hub</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        What fires, what gets held back, and why.
      </Text>
      <Spacer size={4} />

      <KpiRow prefs={prefs.data} entries={log.data?.entries} />
      <Spacer size={4} />

      <TabRow tab={tab} onChange={setTab} />
      <Spacer size={4} />

      <ScrollView showsVerticalScrollIndicator={false}>
        {tab === 'rules' ? (
          <RulesTab prefs={prefs.data} />
        ) : (
          <LogTab entries={log.data?.entries} />
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

// -------------------- KPI row (AH-1) --------------------

/**
 * Reference .kpi tiles (automation.jsx:15-20) for the metrics with REAL
 * backing only — see ../stats.ts for each tile's confirmed source and why
 * "Saved analyst hours" is absent. Tile + wrap styles match the Command
 * Center KPI row (2-up at narrow width).
 */
const KpiRow: React.FC<{
  prefs: AlertPreference[] | undefined;
  entries: Automation.AutomationLogEntry[] | undefined;
}> = ({ prefs, entries }) => (
  <View style={styles.kpiRow}>
    {hubKpis(prefs, entries, new Date()).map(({ label, value }) => (
      <Card key={label} style={styles.kpiTile}>
        <Text variant="label" color="tertiary">
          {label}
        </Text>
        <Spacer size={1} />
        <Text variant="kpiVal">{value}</Text>
      </Card>
    ))}
  </View>
);

// -------------------- Tabs (AH-4) --------------------

/**
 * Reference .tab-row / .tab scale (styles.css:262-264): radius-5 container,
 * 2px padding + 2px gap, radius-3 tabs at 3×10 padding, 11px text (bodySm,
 * the closest variant at 11.5), active = --elev-2 fill. The visual height is
 * ~22px, so each tab carries 12px vertical hitSlop to keep the touch target
 * ≥44px without inflating the drawn scale.
 */
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

// -------------------- Rules (AH-2) --------------------

const RulesTab: React.FC<{ prefs: AlertPreference[] | undefined }> = ({
  prefs,
}) => {
  const frequencyOf = (category: string): string => {
    const row = (prefs ?? []).find(
      (p) => p.type === category && p.channel === 'in_app',
    );
    return row ? FREQUENCY_COPY[row.frequency].label : '—';
  };

  return (
    <>
      <Card
        header={
          <CardHeader title="Rules" sub={`${ALERT_CATEGORIES.length} CATEGORIES`} />
        }
      >
        <HairlineRowList>
          {ALERT_CATEGORIES.map((category) => (
            <RuleRow
              key={category}
              category={category}
              label={CATEGORY_COPY[category].label}
              description={CATEGORY_COPY[category].description}
              frequency={frequencyOf(category)}
              active={frequencyOf(category) !== FREQUENCY_COPY.off.label}
            />
          ))}
        </HairlineRowList>
      </Card>
      <Spacer size={2} />
      <Text variant="caption" color="tertiary">
        Edit these in Settings → Notification preferences.
      </Text>
    </>
  );
};

/**
 * One rules row (reference automation.jsx:28-39, row-level anatomy only):
 * mono category chip — the real analog of the reference's trigger chip —
 * then label/description, then the in-app cadence as a mono chip (teal wash
 * when on). Read-only on purpose: no toggle is rendered because no edit
 * action exists on this screen (see the module note above).
 */
const RuleRow: React.FC<{
  category: string;
  label: string;
  description: string;
  frequency: string;
  active: boolean;
}> = ({ category, label, description, frequency, active }) => {
  const gx = useGx();
  return (
  <View style={styles.row}>
    <View style={[gx.chip, styles.trigChip]}>
      <Text variant="caption" style={gx.chipText}>
        {category.toUpperCase()}
      </Text>
    </View>
    <View style={{ flex: 1 }}>
      <Text variant="body">{label}</Text>
      <Spacer size={1} />
      <Text variant="bodySm" color="secondary">
        {description}
      </Text>
    </View>
    <View style={[gx.chip, styles.freqChip, active && gx.chipTeal]}>
      <Text variant="caption" style={active ? gx.chipTealText : gx.chipText}>
        {frequency}
      </Text>
    </View>
  </View>
  );
};

// -------------------- Log (AH-3) --------------------

const LogTab: React.FC<{
  entries: Automation.AutomationLogEntry[] | undefined;
}> = ({ entries }) => {
  const rows = toFeedRows(entries ?? []);

  if (rows.length === 0) {
    return (
      <EmptyState
        title="Nothing in the log yet"
        description="Every delivered, digested, or suppressed notification will be recorded here."
      />
    );
  }

  return (
    <Card
      header={<CardHeader title="Action log" sub={`${rows.length} ENTRIES`} />}
    >
      <HairlineRowList>
        {rows.map((row) => (
          <LogRow key={row.id} row={row} />
        ))}
      </HairlineRowList>
    </Card>
  );
};

/** Outcome tone → gx chip wash, exhaustive on FeedTone (DraftCard precedent). */
function chipToneStyle(tone: FeedTone, gx: Gx): {
  chip: ViewStyle | undefined;
  text: TextStyle;
} {
  switch (tone) {
    case 'positive':
      return { chip: gx.chipTeal, text: gx.chipTealText };
    case 'warn':
      return { chip: gx.chipWarn, text: gx.chipWarnText };
    case 'danger':
      return { chip: gx.chipNeg, text: gx.chipNegText };
    case 'neutral':
      return { chip: undefined, text: gx.chipText };
  }
}

/**
 * One log row (reference automation.jsx:78-98, row-level anatomy only):
 * fixed-width mono timestamp column, title/subtitle, OK/SKIP/FAIL outcome
 * chip. Pressing the row still toggles the Channel/Trigger/Reason detail
 * block (the prior wave's wiring) — same Pressable, same detail lines.
 */
const LogRow: React.FC<{ row: FeedRow }> = ({ row }) => {
  const t = useTheme();
  const gx = useGx();
  const [expanded, setExpanded] = useState(false);
  const tone = chipToneStyle(row.tone, gx);
  const ts = logTimestamp(row.createdAt);
  return (
    <Pressable
      onPress={() => setExpanded((v) => !v)}
      accessibilityRole="button"
      accessibilityLabel={`${row.title} — ${expanded ? 'hide' : 'show'} details`}
    >
      <View style={styles.row}>
        <View style={styles.tsCol}>
          <Text variant="mono" color="secondary">
            {ts.time}
          </Text>
          {ts.date ? (
            <Text variant="caption" color="tertiary">
              {ts.date}
            </Text>
          ) : null}
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
        </View>
        <View style={[gx.chip, styles.outcomeChip, tone.chip]}>
          <Text variant="caption" style={tone.text}>
            {outcomeChipLabel(row.tone)}
          </Text>
        </View>
        <View style={styles.expandIcon}>
          <Icon name={expanded ? 'ChevronUp' : 'ChevronDown'} size="sm" color="tertiary" />
        </View>
      </View>
      {expanded ? (
        <View style={[styles.detailBlock, { borderTopColor: t.colors.border.subtle }]}>
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
    </Pressable>
  );
};

const styles = StyleSheet.create({
  // Command Center KPI row verbatim: growing ~30%-basis tiles with a 150px
  // floor sit 3-across on desktop and wrap 2+1 inside a narrow viewport.
  kpiRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  kpiTile: { flexGrow: 1, flexBasis: '30%', minWidth: 150 },
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
  row: { flexDirection: 'row', alignItems: 'flex-start', columnGap: 10 },
  // Fixed-width mono category column: VERIFICATION (the widest key) at
  // caption-mono 10px sets the floor so all four chips align flush.
  trigChip: { minWidth: 88, justifyContent: 'center', alignSelf: 'flex-start' },
  freqChip: { alignSelf: 'flex-start' },
  // Reference Timestamp cell (automation.jsx:78 width 130 for HH:MM:SS): the
  // stacked time+date column needs 64 at mono 11.5.
  tsCol: { width: 64 },
  outcomeChip: { alignSelf: 'flex-start', minWidth: 40, justifyContent: 'center' },
  expandIcon: { marginTop: 2 },
  detailBlock: {
    marginTop: 10,
    paddingTop: 8,
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
