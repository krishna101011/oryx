import React, { useState } from 'react';
import { ScrollView, TextInput, StyleSheet } from 'react-native';
import { Button, Card, Screen, Spacer, Text, useTheme } from '@oryx/design-system';
import type { ManualIngestResponse } from '@oryx/shared-types';
import { FeatureGate } from '../../../components/FeatureGate';
import { useMe } from '../../../hooks/useMe';
import { isApiError } from '../../../lib/errors';
import { useAppSelector } from '../../../store';
import { intakeApi } from '../api/intake';

/**
 * PLATFORM ADMIN ONLY (CR-8, §15.2).
 *
 * Defense in depth: (1) the route is only mounted for platform admins
 * (SettingsStack), (2) this screen re-checks the flag + admin bit, and
 * (3) the endpoint enforces `require_platform_admin` server-side — the
 * only check that actually matters. Every submission is audit-logged
 * server-side.
 */
export const ManualIngestScreen: React.FC = () => {
  const me = useMe();
  if (!me.data?.account.isPlatformAdmin) {
    // No "request access" affordance by design (§15.2).
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Card variant="default">
          <Text variant="body" color="secondary">
            This surface is restricted to platform operators.
          </Text>
        </Card>
      </Screen>
    );
  }
  return (
    <FeatureGate flag="ff_intake_manual" name="Manual ingest" icon="PenLine">
      <ManualIngestForm />
    </FeatureGate>
  );
};

const ManualIngestForm: React.FC = () => {
  const t = useTheme();
  const workspaceId = useAppSelector((s) => s.auth.workspaceId);
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [bodyText, setBodyText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ManualIngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!workspaceId) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await intakeApi.manualIngest({
        workspace_id: workspaceId,
        title: title.trim(),
        url: url.trim() || null,
        body_text: bodyText.trim() || null,
      });
      setResult(res);
      setTitle('');
      setUrl('');
      setBodyText('');
    } catch (e) {
      setError(isApiError(e) ? e.message : 'Ingest failed.');
    } finally {
      setBusy(false);
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

  const canSubmit =
    title.trim().length > 0 && (url.trim().length > 0 || bodyText.trim().length > 0);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="brand">
          OPERATOR TOOL
        </Text>
        <Spacer size={2} />
        <Text variant="display">Manual ingest</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Items go through the full pipeline — normalize, dedupe, persist,
          emit. Submissions are audit-logged.
        </Text>
        <Spacer size={6} />

        <TextInput
          style={inputStyle}
          placeholder="Title"
          placeholderTextColor={t.colors.text.tertiary}
          value={title}
          onChangeText={setTitle}
        />
        <Spacer size={2} />
        <TextInput
          style={inputStyle}
          placeholder="https://… (optional if body given)"
          placeholderTextColor={t.colors.text.tertiary}
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          keyboardType="url"
        />
        <Spacer size={2} />
        <TextInput
          style={[...inputStyle, styles.multiline]}
          placeholder="Body text (optional if URL given)"
          placeholderTextColor={t.colors.text.tertiary}
          value={bodyText}
          onChangeText={setBodyText}
          multiline
        />
        <Spacer size={4} />
        <Button
          label={busy ? 'Ingesting…' : 'Ingest item'}
          variant="primary"
          fullWidth
          disabled={!canSubmit || busy}
          onPress={submit}
        />

        {result ? (
          <>
            <Spacer size={4} />
            <Card variant="default">
              <Text variant="bodySm">
                {result.outcome === 'inserted'
                  ? 'Ingested.'
                  : 'Skipped — already known (dedupe).'}
              </Text>
              <Spacer size={1} />
              <Text variant="caption" color="tertiary">
                fingerprint {result.fingerprint.slice(0, 16)}…
              </Text>
            </Card>
          </>
        ) : null}
        {error ? (
          <>
            <Spacer size={3} />
            <Text variant="bodySm" color="danger">
              {error}
            </Text>
          </>
        ) : null}
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
  multiline: { minHeight: 120, textAlignVertical: 'top' },
});
