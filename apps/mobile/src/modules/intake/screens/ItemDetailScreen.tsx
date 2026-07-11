import React from 'react';
import { Linking, ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useRoute } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Divider,
  Pressable,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { IntakeItemDetail } from '@oryx/shared-types';
import type { SettingsStackParamList } from '../../../navigation/types';
import { EmptyState } from '../../../components/EmptyState';
import { intakeApi } from '../api/intake';

/**
 * One ingested item's REAL content (GET /intake/items/{id}) — what an
 * Activity "New item ingested" row and a web search result open onto:
 * headline, source, sender, body text, extracted links. Un-normalized items
 * (the normalizer hasn't reached them yet) render honestly as "processing",
 * not as an error.
 */
export const ItemDetailScreen: React.FC = () => {
  const route = useRoute<RouteProp<SettingsStackParamList, 'IntakeItemDetail'>>();
  const { itemId } = route.params;

  const item = useQuery<IntakeItemDetail>({
    queryKey: ['intake', 'item', itemId],
    queryFn: () => intakeApi.getItem(itemId),
  });

  if (item.isLoading) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={120} />
      </Screen>
    );
  }

  if (!item.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <EmptyState
          title="Item unavailable"
          description="This item may have been removed with its source."
        />
      </Screen>
    );
  }

  const d = item.data;
  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="brand">
          INGESTED ITEM
        </Text>
        <Spacer size={2} />
        <Text variant="display">{d.subject ?? 'Processing…'}</Text>
        {d.subject === null ? (
          <>
            <Spacer size={2} />
            <Text variant="bodySm" color="secondary">
              Received, awaiting content extraction.
            </Text>
          </>
        ) : null}
        <Spacer size={6} />

        <Card variant="elevated">
          <Row label="Source" value={d.sourceName} />
          <Divider />
          <Row label="Provider" value={d.providerName} />
          <Divider />
          <Row
            label="Sender"
            value={d.senderLabel ?? d.senderDomain ?? '—'}
          />
          <Divider />
          <Row label="Received" value={new Date(d.receivedAt).toLocaleString()} />
        </Card>

        {d.bodyText ? (
          <>
            <Spacer size={4} />
            <Card variant="default">
              <Text variant="bodySm" color="secondary">
                {d.bodyText}
              </Text>
            </Card>
          </>
        ) : null}

        {d.links.length > 0 ? (
          <>
            <Spacer size={4} />
            <Text variant="label" color="tertiary">
              LINKS
            </Text>
            <Spacer size={2} />
            {d.links.map((link) => (
              <LinkRow key={link.url} url={link.url} anchor={link.anchor} />
            ))}
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const Row: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.row}>
    <Text variant="bodySm" color="tertiary">
      {label}
    </Text>
    <Text variant="bodySm" style={{ flexShrink: 1, textAlign: 'right' }}>
      {value}
    </Text>
  </View>
);

const LinkRow: React.FC<{ url: string; anchor: string }> = ({ url, anchor }) => {
  const t = useTheme();
  return (
    <Pressable onPress={() => Linking.openURL(url)}>
      <Card variant="default">
        <Text variant="bodySm" style={{ color: t.colors.semantic.info }} numberOfLines={1}>
          {anchor || url}
        </Text>
        {anchor ? (
          <>
            <Spacer size={1} />
            <Text variant="caption" color="tertiary" numberOfLines={1}>
              {url}
            </Text>
          </>
        ) : null}
      </Card>
      <Spacer size={2} />
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    columnGap: 12,
  },
});
