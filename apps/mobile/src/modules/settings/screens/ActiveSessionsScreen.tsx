import React from 'react';
import { ScrollView, View, StyleSheet } from 'react-native';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Icon,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@anant/design-system';
import type { Session } from '@anant/shared-types';
import { apiClient } from '../../../lib/api/client';
import { useAppDispatch } from '../../../store';
import { signout } from '../../../store/thunks/auth';

export const ActiveSessionsScreen: React.FC = () => {
  const t = useTheme();
  const queryClient = useQueryClient();
  const dispatch = useAppDispatch();

  const sessions = useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: () => apiClient().get<Session[]>('/sessions'),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => apiClient().delete(`/sessions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sessions'] }),
  });

  const signOutAll = useMutation({
    mutationFn: () => apiClient().post('/auth/signout-all'),
    onSuccess: () => dispatch(signout()),
  });

  return (
    <Screen background="primary">
      <ScrollView>
        <Spacer size={6} />
        <Text variant="display">Sessions</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Devices currently signed in.
        </Text>
        <Spacer size={6} />

        {(sessions.data ?? []).map((s) => (
          <View key={s.id}>
            <Card variant="default">
              <View style={styles.row}>
                <View style={[styles.iconWrap, { backgroundColor: t.colors.accent.goldGlow }]}>
                  <Icon name="Smartphone" color="gold" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text variant="body">
                    {s.deviceLabel} {s.current ? '· This device' : ''}
                  </Text>
                  <Spacer size={1} />
                  <Text variant="caption" color="tertiary">
                    Last active {new Date(s.lastUsedAt).toLocaleString()}
                  </Text>
                </View>
                {!s.current && (
                  <Button
                    label="Revoke"
                    variant="ghost"
                    size="sm"
                    onPress={() => revoke.mutate(s.id)}
                  />
                )}
              </View>
            </Card>
            <Spacer size={2} />
          </View>
        ))}

        <Spacer size={6} />
        <Button
          label="Sign out everywhere"
          variant="danger"
          fullWidth
          onPress={() => signOutAll.mutate()}
        />
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  iconWrap: {
    width: 36, height: 36, borderRadius: 8,
    alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
});
