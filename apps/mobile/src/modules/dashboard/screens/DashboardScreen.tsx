import React from 'react';
import { StyleSheet, View } from 'react-native';
import {
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Pressable,
  Screen,
  SkeletonRow,
  SkeletonTile,
  Spacer,
  Text,
  useGx,
} from '@oryx/design-system';
import { useMe } from '../../../hooks/useMe';
import { navigateSettingsScreen } from '../../../navigation/navigationRef';
import { useIntakeStatus, useRecentIntakeItems } from '../../intake/hooks/useIntakeSources';
import { HeroWash } from '../components/HeroWash';
import { heroKicker, heroSummary } from '../hero';
import {
  draftsStatValue,
  sourcesStatValue,
  todayCountSub,
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
 * One hero KPI tile — reference .kpi (styles.css:363-372): mono uppercase
 * label + kpiVal value on a bordered panel. Deliberately NO sparkline and NO
 * delta: no real time series exists for any of these three metrics (the
 * analytics rollups measure daily pipeline EVENTS — intake_items_received,
 * claims_verified, drafts_published — not the stock counts these tiles show),
 * and no prior-period source exists either. Nothing is invented.
 */
const KpiTile: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Card style={styles.kpiTile}>
    <Text variant="label" color="tertiary">
      {label}
    </Text>
    <Spacer size={1} />
    <Text variant="kpiVal">{value}</Text>
  </Card>
);

/**
 * Command Center. Every number traces to a confirmed real field:
 * SOURCES = IntakeStatusSummary.total (GET /intake/status); VERIFIED =
 * /auth/me verification.verifiedCount; DRAFTS = /auth/me content.draftCount;
 * the hero sentence adds verification.pendingReviewCount. "Today" shows the
 * real most-recent ingested items (GET /intake/items/recent) — the Activity
 * tab owns notification rows.
 */
export const DashboardScreen: React.FC = () => {
  const gx = useGx();
  const me = useMe();
  const intakeStatus = useIntakeStatus();
  const recentItems = useRecentIntakeItems();
  const today = todayPanelState(recentItems.data);
  const kpiLoading = intakeStatus.isLoading || me.isLoading;
  return (
    <Screen background="primary">
      <View style={styles.hero}>
        <HeroWash />
        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          {heroKicker(new Date())}
        </Text>
        <Spacer size={2} />
        <Text variant="display">Good morning.</Text>
        <Spacer size={1} />
        <Text variant="body" color="secondary">
          {heroSummary(intakeStatus.data, me.data).map((seg, i) =>
            seg.strong ? (
              <Text key={i} variant="body" color="primary">
                {seg.text}
              </Text>
            ) : (
              seg.text
            ),
          )}
        </Text>

        <Spacer size={5} />

        <View style={styles.kpiRow}>
          {kpiLoading ? (
            <>
              <SkeletonTile style={styles.kpiTile} />
              <SkeletonTile style={styles.kpiTile} />
              <SkeletonTile style={styles.kpiTile} />
            </>
          ) : (
            <>
              <KpiTile label="SOURCES" value={sourcesStatValue(intakeStatus.data)} />
              <KpiTile label="VERIFIED" value={verifiedStatValue(me.data)} />
              <KpiTile label="DRAFTS" value={draftsStatValue(me.data)} />
            </>
          )}
        </View>
        <Spacer size={4} />
      </View>

      <Card header={<CardHeader title="Today" sub={todayCountSub(today)} />}>
        {today.kind === 'loading' && (
          <HairlineRowList>
            {/* Today row anatomy: a single leading tag chip (~56px, the
                reference's min-width) as the whole head line, 2-line
                headline, source/time meta, chevron gap. */}
            <SkeletonRow leadingWidth={56} titleWidth="85%" />
            <SkeletonRow leadingWidth={56} titleWidth="85%" />
            <SkeletonRow leadingWidth={56} titleWidth="85%" />
          </HairlineRowList>
        )}
        {today.kind === 'empty' && (
          <Text variant="body" color="secondary">
            Nothing to surface yet. Connect a source to begin.
          </Text>
        )}
        {today.kind === 'list' && (
          <HairlineRowList>
            {today.rows.map((row) => {
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
                  <View style={styles.todayRow}>
                    <View style={[gx.chip, gx.chipIndigo, styles.tagChip]}>
                      <Text variant="caption" style={gx.chipIndigoText}>
                        {row.tag}
                      </Text>
                    </View>
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
          </HairlineRowList>
        )}
      </Card>

    </Screen>
  );
};

const styles = StyleSheet.create({
  // The wash needs a positioned, clipped box to fill; the hero is that box.
  hero: { position: 'relative', overflow: 'hidden' },
  // 2-up at narrow width: three growing tiles at ~30% basis with a 150px
  // floor wrap 2+1 inside a ~390px viewport and sit 3-across on desktop.
  kpiRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  kpiTile: { flexGrow: 1, flexBasis: '30%', minWidth: 150 },
  todayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  // Reference brief-bullet chip: min-width + centered content
  // (command-center.jsx:84); alignSelf keeps it from stretching row-tall.
  tagChip: { minWidth: 56, justifyContent: 'center', alignSelf: 'flex-start' },
  chevron: { marginTop: 4, marginLeft: 8 },
});
