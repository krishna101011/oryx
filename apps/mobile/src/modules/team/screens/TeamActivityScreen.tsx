import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Card, CardHeader, HairlineRowList, Icon, Screen, Spacer, Text } from '@oryx/design-system';
import { useMe } from '../../../hooks/useMe';
import { describeActivityEvent } from '../activityCopy';
import { useTeamActivity } from '../hooks/useTeamActivity';

/**
 * Full Team activity history — invited/joined/removed events for the
 * current workspace, real data from GET /workspaces/activity (Team
 * promotion wave, 2026-07-26). Still a read-only factual log, not a
 * conversation — real-time messaging lives on its own screen,
 * TeamChatScreen, reached from TeamHome.
 */
export const TeamActivityScreen: React.FC = () => {
  const me = useMe();
  const activity = useTeamActivity();
  const events = activity.data?.events ?? [];

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Activity</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Invites, joins, and removals for this workspace.
        </Text>
        <Spacer size={6} />

        {events.length > 0 ? (
          <Card header={<CardHeader title="Activity" sub={`${events.length} EVENTS`} />}>
            <HairlineRowList>
              {events.map((event) => {
                const copy = describeActivityEvent(event, me.data?.account.id);
                return (
                  <View key={event.id} style={styles.row}>
                    <Icon name={copy.icon} size="sm" color="secondary" />
                    <Spacer size={3} axis="horizontal" />
                    <View style={{ flex: 1 }}>
                      <Text variant="body">{copy.text}</Text>
                      <Spacer size={1} />
                      <Text variant="caption" color="tertiary">
                        {new Date(event.createdAt).toLocaleString()}
                      </Text>
                    </View>
                  </View>
                );
              })}
            </HairlineRowList>
          </Card>
        ) : !activity.isLoading ? (
          <Card>
            <View style={styles.empty}>
              <Icon name="Users" size="lg" color="secondary" />
              <Spacer size={3} />
              <Text variant="body" color="secondary" style={{ textAlign: 'center' }}>
                No team activity yet.
              </Text>
            </View>
          </Card>
        ) : null}

        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  empty: { padding: 24, alignItems: 'center' },
});
