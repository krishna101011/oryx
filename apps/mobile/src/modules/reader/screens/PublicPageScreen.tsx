import React from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useRoute } from '@react-navigation/native';
import { useQuery } from '@tanstack/react-query';
import { Screen, Spacer, Text, useTheme } from '@oryx/design-system';
import type { RootStackParamList } from '../../../navigation/types';
import { PublicPageNotFoundError, fetchPublicPage } from '../api/publicPages';
import { presentPublicCitations } from '../citations';
import { splitParagraphs } from '../paragraphs';

function formatPublishedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Public Reader Rev 1 — the genuinely unauthenticated reader screen.
 *
 * One real network call (fetchPublicPage combines content + citations
 * server-side, see reader/api/publicPages.ts), plain-paragraph rendering
 * (no markdown library this wave — recon confirmed none exists in
 * apps/mobile's dependencies), and a real 404 state for an unknown/expired
 * slug. Never touches useMe()/auth state — RootNavigator only mounts this
 * screen on a branch that never mounts AuthenticatedRootNavigator.
 */
export const PublicPageScreen: React.FC = () => {
  const t = useTheme();
  const route = useRoute<RouteProp<RootStackParamList, 'PublicPage'>>();
  const { slug } = route.params;

  const query = useQuery({
    queryKey: ['publicPage', slug],
    queryFn: () => fetchPublicPage(slug),
    retry: false,
  });

  if (query.isError) {
    const notFound = query.error instanceof PublicPageNotFoundError;
    return (
      <Screen background="primary">
        <View style={styles.center}>
          <Text variant="h2" align="center">
            {notFound ? "This page isn't available" : 'Something went wrong'}
          </Text>
          <Spacer size={2} />
          <Text variant="body" color="secondary" align="center">
            {notFound
              ? 'The link may be incorrect, or the page may have expired.'
              : 'Please try again in a moment.'}
          </Text>
        </View>
      </Screen>
    );
  }

  if (!query.data) {
    return (
      <Screen background="primary">
        <View style={styles.center}>
          <ActivityIndicator color={t.colors.accent.amber} />
        </View>
      </Screen>
    );
  }

  const page = query.data;
  const paragraphs = splitParagraphs(page.content);
  const citationRows = presentPublicCitations(page.citations);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          {formatPublishedAt(page.publishedAt)}
        </Text>
        <Spacer size={3} />
        {paragraphs.map((paragraph, i) => (
          <React.Fragment key={i}>
            <Text variant="body">{paragraph}</Text>
            <Spacer size={4} />
          </React.Fragment>
        ))}
        {citationRows.length > 0 ? (
          <>
            <Spacer size={2} />
            <Text variant="caption" color="tertiary">
              SOURCES
            </Text>
            <Spacer size={2} />
            {citationRows.map((row) => (
              <View key={row.key} style={styles.sourceRow}>
                <Text variant="bodySm">{row.headline}</Text>
                <Text variant="caption" color={row.tone}>
                  {row.tierLabel} · {row.epistemicLabel}
                </Text>
              </View>
            ))}
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sourceRow: { marginTop: 8 },
});
