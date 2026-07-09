import React from 'react';
import { Linking, ScrollView, StyleSheet, View } from 'react-native';
import {
  Card,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
} from '@oryx/design-system';
import type { PublicationStatus } from '@oryx/shared-types';
import { usePublications } from '../hooks/usePublishing';
import { ProvenanceSection } from '../components/ProvenanceSection';
import { EmptyState } from '../../../components/EmptyState';

const STATUS_COLOR: Record<PublicationStatus, 'secondary' | 'brand' | 'danger' | 'tertiary'> = {
  pending: 'tertiary',
  delivering: 'brand',
  delivered: 'brand',
  failed: 'danger',
  cancelled: 'tertiary',
};

export const PublishHistoryScreen: React.FC = () => {
  const publications = usePublications();

  return (
    <Screen background="primary">
      <Spacer size={6} />
      <Text variant="caption" color="brand">
        PUBLISHING
      </Text>
      <Spacer size={2} />
      <Text variant="display">History</Text>
      <Spacer size={2} />
      <Text variant="body" color="secondary">
        Every delivery attempt and its outcome.
      </Text>
      <Spacer size={6} />

      <ScrollView showsVerticalScrollIndicator={false}>
        {publications.isLoading ? (
          <Skeleton height={72} />
        ) : (publications.data ?? []).length === 0 ? (
          <EmptyState
            title="No publications yet"
            description="Once you publish a draft, delivery status for each channel shows up here."
          />
        ) : (
          (publications.data ?? []).map((p) => (
            <View key={p.id}>
              <Card variant="default">
                <View style={styles.row}>
                  <Text variant="body">v{p.versionNumber}</Text>
                  <Text variant="caption" color={STATUS_COLOR[p.status]}>
                    {p.status.toUpperCase()}
                  </Text>
                </View>
                <Spacer size={1} />
                <Text variant="caption" color="tertiary">
                  {new Date(p.createdAt).toLocaleString()}
                </Text>
                {p.errorMessage ? (
                  <>
                    <Spacer size={1} />
                    <Text variant="caption" color="danger">
                      {p.errorMessage}
                    </Text>
                  </>
                ) : null}
                {p.externalUrl ? (
                  <>
                    <Spacer size={1} />
                    <Pressable onPress={() => Linking.openURL(p.externalUrl as string)}>
                      <Text variant="caption" color="brand">
                        View published →
                      </Text>
                    </Pressable>
                  </>
                ) : null}
                <Spacer size={1} />
                <ProvenanceSection publicationId={p.id} />
              </Card>
              <Spacer size={2} />
            </View>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
