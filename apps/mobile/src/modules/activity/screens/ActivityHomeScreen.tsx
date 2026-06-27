import React from 'react';
import { ScrollView, View, StyleSheet } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Icon,
  Pressable,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type {
  ActivityInboxResponse,
  ActivityItem,
} from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';
import { EmptyState } from '../../../components/EmptyState';

export const ActivityHomeScreen: React.FC = () => {
  const queryClient = useQueryClient();

  const inbox = useQuery<ActivityInboxResponse>({
    queryKey: ['activity', 'inbox'],
    queryFn: () => apiClient().get<ActivityInboxResponse>('/activity/inbox'),
  });

  const markRead = useMutation({
    mutationFn: (id: string) => apiClient().post(`/activity/inbox/${id}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activity', 'inbox'] });
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });

  const items = inbox.data?.items ?? [];

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        ACTIVITY
      </Text>
      <Spacer size={2} />
      <Text variant="display">Recent</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        Security events and system updates.
      </Text>
      <Spacer size={6} />

      <ScrollView showsVerticalScrollIndicator={false}>
        {items.length === 0 ? (
          <EmptyState
            title="Nothing to report"
            description="Security events and account activity will show up here as they happen."
          />
        ) : (
          items.map((item) => (
            <View key={item.id}>
              <Pressable
                onPress={() => !item.readAt && markRead.mutate(item.id)}
              >
                <ActivityCard item={item} />
              </Pressable>
              <Spacer size={2} />
            </View>
          ))
        )}
      </ScrollView>
    </Screen>
  );
};

const ActivityCard: React.FC<{ item: ActivityItem }> = ({ item }) => {
  const t = useTheme();
  const unread = !item.readAt;
  const icon = item.type === 'security' ? 'ShieldAlert' : 'BellRing';
  return (
    <Card variant={unread ? 'elevated' : 'default'}>
      <View style={styles.row}>
        <View
          style={[
            styles.iconWrap,
            { backgroundColor: t.colors.accent.tealGlow },
          ]}
        >
          <Icon name={icon} color={unread ? 'brand' : 'tertiary'} />
        </View>
        <View style={{ flex: 1 }}>
          <Text variant="body">{item.title}</Text>
          {item.body ? (
            <>
              <Spacer size={1} />
              <Text variant="bodySm" color="secondary">
                {item.body}
              </Text>
            </>
          ) : null}
          <Spacer size={1} />
          <Text variant="caption" color="tertiary">
            {new Date(item.createdAt).toLocaleString()}
          </Text>
        </View>
        {unread && (
          <View
            style={[
              styles.dot,
              { backgroundColor: t.colors.accent.teal },
            ]}
          />
        )}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 8, marginLeft: 8 },
});
