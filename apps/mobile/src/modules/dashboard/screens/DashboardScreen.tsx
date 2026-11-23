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
  useTheme,
} from '@oryx/design-system';
import { useMe } from '../../../hooks/useMe';
import {
  navigateContentScreen,
  navigateResearchScreen,
  navigateSettingsScreen,
} from '../../../navigation/navigationRef';
import { useIntakeStatus, useRecentIntakeItems } from '../../intake/hooks/useIntakeSources';
import { HeroWash } from '../components/HeroWash';
import { heroGreeting, heroKicker, heroSummary } from '../hero';
import {
  draftsStatValue,
  sourceSetupState,
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
    <Text variant="label" color="tertiary" numberOfLines={1}>
      {label}
    </Text>
    <Spacer size={1} />
    <Text variant="kpiVal" numberOfLines={1}>
      {value}
    </Text>
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
  const theme = useTheme();
  const me = useMe();
  const intakeStatus = useIntakeStatus();
  const recentItems = useRecentIntakeItems();
  const now = new Date();
  const today = todayPanelState(recentItems.data);
  const setupState = sourceSetupState(
    intakeStatus.data,
    intakeStatus.isLoading,
    intakeStatus.isError,
  );
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
            {heroKicker(now)}
          </Text>
          <Spacer size={2} />
          <Text variant="display">{heroGreeting(now)}</Text>
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

          <View style={styles.kpiRow} testID="dashboard-kpi-row">
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
              title={
                setupState === 'loading'
                  ? 'Checking your workspace'
                  : setupState === 'error'
                    ? 'Sources unavailable'
                    : setupState === 'empty'
                      ? 'Get started'
                      : 'Next steps'
              }
              sub={
                setupState === 'loading'
                  ? 'Checking connected sources'
                  : setupState === 'error'
                    ? 'Could not confirm your connections'
                    : setupState === 'empty'
                      ? 'Connect your first information source'
                      : 'Move intelligence through ORYX'
              }
            />
          }
        >
          {setupState === 'loading' ? (
            <View>
              <Text variant="body" color="secondary">
                Your workspace is loading. Your next steps will appear here shortly.
              </Text>
              <Spacer size={3} />
              <SkeletonRow leadingWidth={56} titleWidth="85%" />
            </View>
          ) : setupState === 'error' ? (
            <View>
              <Text variant="body" color="secondary">
                ORYX couldn't load your source status. Your existing connections haven't been changed.
              </Text>
              <Spacer size={3} />
              <Button
                label="Try again"
                variant="secondary"
                fullWidth
                testID="dashboard-retry-source-status"
                onPress={() => { void intakeStatus.refetch(); }}
              />
            </View>
          ) : setupState === 'empty' ? (
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
              <Pressable
                style={[styles.actionRow, { borderBottomColor: theme.colors.border.default }]}
                testID="dashboard-open-research"
                onPress={() => navigateResearchScreen('ResearchWorkspaceList')}
                accessibilityRole="button"
                accessibilityLabel="Open research. Explore your workspace and investigate incoming information."
              >
                <View style={[styles.actionIcon, gx.navItemActive]}>
                  <Icon name="Search" size="md" color="brand" />
                </View>
                <View style={styles.actionCopy}>
                  <Text variant="body">Open research</Text>
                  <Text variant="caption" color="tertiary">
                    Explore your workspace and investigate information.
                  </Text>
                </View>
                <Text variant="caption" color="tertiary">01</Text>
                <Icon name="ChevronRight" size="sm" color="tertiary" />
              </Pressable>
              <Pressable
                style={[styles.actionRow, { borderBottomColor: theme.colors.border.default }]}
                testID="dashboard-generate-draft"
                onPress={() => navigateContentScreen('GenerateDraft')}
                accessibilityRole="button"
                accessibilityLabel="Generate a draft. Turn research into a clear first draft."
              >
                <View style={[styles.actionIcon, gx.navItemActive]}>
                  <Icon name="FileText" size="md" color="brand" />
                </View>
                <View style={styles.actionCopy}>
                  <Text variant="body">Generate a draft</Text>
                  <Text variant="caption" color="tertiary">
                    Turn research into a clear first draft.
                  </Text>
                </View>
                <Text variant="caption" color="tertiary">02</Text>
                <Icon name="ChevronRight" size="sm" color="tertiary" />
              </Pressable>
              <Pressable
                style={[styles.actionRow, { borderBottomColor: theme.colors.border.default }]}
                testID="dashboard-review-claims"
                onPress={() => navigateSettingsScreen('VerificationQueue')}
                accessibilityRole="button"
                accessibilityLabel="Review claims. Check evidence and resolve items awaiting verification."
              >
                <View style={[styles.actionIcon, gx.navItemActive]}>
                  <Icon name="ShieldCheck" size="md" color="brand" />
                </View>
                <View style={styles.actionCopy}>
                  <Text variant="body">Review claims</Text>
                  <Text variant="caption" color="tertiary">
                    Check evidence and resolve items awaiting verification.
                  </Text>
                </View>
                <Text variant="caption" color="tertiary">03</Text>
                <Icon name="ChevronRight" size="sm" color="tertiary" />
              </Pressable>
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
                  : intakeStatus.data && intakeStatus.data.total > 0
                    ? "Your intelligence feed is quiet. Connect or manage a source to bring new information into ORYX."
                    : "Source status couldn't be confirmed, so ORYX can't tell whether new information is expected. Try again above."}
              </Text>
              {intakeStatus.data !== undefined && intakeStatus.data.total > 0 ? (
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
  // Keep all three real KPIs on one balanced row, including narrow phones.
  kpiRow: { flexDirection: 'row', flexWrap: 'nowrap', gap: 8 },
  kpiTile: { flex: 1, minWidth: 0 },
  actions: { gap: 0 },
  actionRow: {
    minHeight: 68,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  actionIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionCopy: { flex: 1, minWidth: 0, gap: 3 },
  todayRow: { flexDirection: 'row', alignItems: 'flex-start' },
  tagChip: { minWidth: 56, justifyContent: 'center', alignSelf: 'flex-start' },
  chevron: { marginTop: 4, marginLeft: 8 },
});
