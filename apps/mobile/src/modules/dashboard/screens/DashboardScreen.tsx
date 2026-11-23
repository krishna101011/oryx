import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  Button,
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
import {
  navigateContentScreen,
  navigateResearchScreen,
  navigateSettingsScreen,
} from '../../../navigation/navigationRef';
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

/** One hero KPI tile. Values come from real API fields; no invented deltas or sparklines. */
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
 * Command Center. Every metric traces to a confirmed API field. The Next steps
 * actions use registered navigation destinations: Research workspace list,
 * draft generation, and the verification queue. Today shows real recent
 * intake items, not notification rows.
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
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
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

        <Card
          header={
            <CardHeader
              title={intakeStatus.data?.total === 0 ? "Get started" : "Next steps"}
              sub={
                intakeStatus.data?.total === 0
                  ? "Connect your first information source"
                  : "Move intelligence through ORYX"
              }
            />
          }
        >
          {intakeStatus.data?.total === 0 ? (
            <View>
              <Text variant="body" color="secondary">
                Bring trusted information into ORYX first. Once a source is connected, you can organize research, verify claims, and create drafts.
              </Text>
              <Spacer size={3} />
              <Button
                label="Connect a source"
                variant="primary"
                fullWidth
                testID="dashboard-connect-first-source"
                onPress={() => navigateSettingsScreen('IntakeHome')}
              />
            </View>
          ) : (
            <View style={styles.actions}>
              <Button
                label="Open research"
                variant="secondary"
                size="sm"
                fullWidth
                testID="dashboard-open-research"
                onPress={() => navigateResearchScreen('ResearchWorkspaceList')}
              />
              <Button
                label="Generate a draft"
                variant="secondary"
                size="sm"
                fullWidth
                testID="dashboard-generate-draft"
                onPress={() => navigateContentScreen('GenerateDraft')}
              />
              <Button
                label="Review claims"
                variant="secondary"
                size="sm"
                fullWidth
                testID="dashboard-review-claims"
                onPress={() => navigateSettingsScreen('VerificationQueue')}
              />
            </View>
          )}
        </Card>

        <Spacer size={4} />

        <Card header={<CardHeader title="Today" sub={todayCountSub(today)} />}>
          {today.kind === 'loading' && (
            <HairlineRowList>
              <SkeletonRow leadingWidth={56} titleWidth="85%" />
              <SkeletonRow leadingWidth={56} titleWidth="85%" />
              <SkeletonRow leadingWidth={56} titleWidth="85%" />
            </HairlineRowList>
          )}
          {today.kind === 'empty' && (
            <View>
              <Text variant="body" color="secondary">
                {intakeStatus.data?.total === 0
                  ? "Your feed will appear here after you connect a source."
                  : "Your intelligence feed is quiet. Connect or manage a source to bring new information into ORYX."}
              </Text>
              {intakeStatus.data?.total !== 0 ? (
                <>
                  <Spacer size={3} />
                  <Button
                    label="Manage sources"
                    variant="secondary"
                    fullWidth
                    testID="dashboard-manage-sources"
                    onPress={() => navigateSettingsScreen('IntakeHome')}
                  />
                </>
              ) : null}
            </View>
          )}
          {today.kind === 'list' && (
            <HairlineRowList>
              {today.rows.map((row) => {
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
        <Spacer size={6} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  content: { paddingBottom: 24 },
  hero: { position: 'relative', overflow: 'hidden' },
  kpiRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  kpiTile: { flexGrow: 1, flexBasis: '30%', minWidth: 150 },
  actions: { gap: 8 },
  todayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  tagChip: { minWidth: 56, justifyContent: 'center', alignSelf: 'flex-start' },
  chevron: { marginTop: 4, marginLeft: 8 },
});
