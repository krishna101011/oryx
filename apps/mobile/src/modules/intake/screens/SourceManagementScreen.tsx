import React, { useState } from 'react';
import { Linking, ScrollView, StyleSheet, TextInput } from 'react-native';
import { Button, Card, Screen, Spacer, Text, useTheme } from '@anant/design-system';
import { useMe } from '../../../hooks/useMe';
import { isApiError } from '../../../lib/errors';
import { intakeApi } from '../api/intake';
import { SourceCard } from '../components/SourceCard';
import { useCreateSource, useIntakeSources } from '../hooks/useIntakeSources';

/**
 * Add and toggle sources. Per-kind availability follows the §14.5 flags;
 * the connect flow is explicit about what each kind can and cannot do
 * (§15.3 — read-only guarantees surfaced inline).
 */
export const SourceManagementScreen: React.FC = () => {
  const t = useTheme();
  const me = useMe();
  const sources = useIntakeSources();
  const create = useCreateSource();

  const [feedName, setFeedName] = useState('');
  const [feedUrl, setFeedUrl] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [gmailBusy, setGmailBusy] = useState(false);

  const flags = me.data?.flags;
  const rssEnabled = flags?.ff_intake_rss ?? false;
  const gmailEnabled = flags?.ff_intake_gmail ?? false;

  const addRss = async () => {
    setFormError(null);
    try {
      await create.mutateAsync({
        name: feedName.trim() || feedUrl.trim(),
        kind: 'rss',
        origin_kind: 'custom',
        config: { feed_url: feedUrl.trim() },
      });
      setFeedName('');
      setFeedUrl('');
    } catch (e) {
      setFormError(isApiError(e) ? e.message : 'Could not add the feed.');
    }
  };

  const connectGmail = async () => {
    setGmailBusy(true);
    setFormError(null);
    try {
      const { authUrl } = await intakeApi.startGmailOauth();
      await Linking.openURL(authUrl);
    } catch (e) {
      setFormError(isApiError(e) ? e.message : 'Could not start the Gmail connection.');
    } finally {
      setGmailBusy(false);
    }
  };

  const inputStyle = [
    styles.input,
    {
      backgroundColor: t.colors.bg.card,
      borderColor: t.colors.border.default,
      color: t.colors.text.primary,
    },
  ];

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="display">Manage sources</Text>
        <Spacer size={6} />

        {rssEnabled ? (
          <Card variant="elevated">
            <Text variant="h2">Add an RSS feed</Text>
            <Spacer size={2} />
            <Text variant="bodySm" color="secondary">
              We fetch the feed on a schedule. Nothing is ever written upstream.
            </Text>
            <Spacer size={3} />
            <TextInput
              style={inputStyle}
              placeholder="Name (optional)"
              placeholderTextColor={t.colors.text.tertiary}
              value={feedName}
              onChangeText={setFeedName}
              autoCapitalize="none"
            />
            <Spacer size={2} />
            <TextInput
              style={inputStyle}
              placeholder="https://example.com/feed.xml"
              placeholderTextColor={t.colors.text.tertiary}
              value={feedUrl}
              onChangeText={setFeedUrl}
              autoCapitalize="none"
              keyboardType="url"
            />
            <Spacer size={3} />
            <Button
              label={create.isPending ? 'Adding…' : 'Add feed'}
              variant="primary"
              fullWidth
              disabled={feedUrl.trim().length === 0 || create.isPending}
              onPress={addRss}
            />
          </Card>
        ) : null}

        {gmailEnabled ? (
          <>
            <Spacer size={4} />
            <Card variant="elevated">
              <Text variant="h2">Connect Gmail</Text>
              <Spacer size={2} />
              <Text variant="bodySm" color="secondary">
                Read-only access to the labels you choose. We never send,
                modify, or delete mail.
              </Text>
              <Spacer size={3} />
              <Button
                label={gmailBusy ? 'Opening…' : 'Connect Gmail'}
                variant="primary"
                fullWidth
                disabled={gmailBusy}
                onPress={connectGmail}
              />
            </Card>
          </>
        ) : null}

        {!rssEnabled && !gmailEnabled ? (
          <Card variant="default">
            <Text variant="body" color="secondary">
              Source connections are rolling out gradually. Nothing is
              available for this workspace yet.
            </Text>
          </Card>
        ) : null}

        {formError ? (
          <>
            <Spacer size={3} />
            <Text variant="bodySm" color="danger">
              {formError}
            </Text>
          </>
        ) : null}

        <Spacer size={6} />
        <Text variant="caption" color="tertiary">
          EXISTING
        </Text>
        <Spacer size={2} />
        {(sources.data ?? []).map((s) => (
          <React.Fragment key={s.id}>
            <SourceCard source={s} />
            <Spacer size={2} />
          </React.Fragment>
        ))}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
});
