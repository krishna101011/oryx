import React, { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import {
  Button,
  Card,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { PublishChannel } from '@oryx/shared-types';
import { CHANNEL_LABEL, ChannelBadge } from '../components/ChannelBadge';
import {
  useCreateTarget,
  useDeleteTarget,
  useHealthCheck,
  useTargets,
} from '../hooks/usePublishing';
import { isApiError } from '../../../lib/errors';

const CHANNELS: PublishChannel[] = [
  'twitter_x',
  'linkedin',
  'email_newsletter',
  'notion',
  'webhook',
  'export',
];

interface KvRow {
  key: string;
  value: string;
}

function kvToObject(rows: KvRow[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const r of rows) {
    const k = r.key.trim();
    if (k) out[k] = r.value;
  }
  return out;
}

export const PublishTargetScreen: React.FC = () => {
  const theme = useTheme();
  const targets = useTargets();
  const create = useCreateTarget();
  const remove = useDeleteTarget();
  const health = useHealthCheck();

  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [channel, setChannel] = useState<PublishChannel>('webhook');
  const [creds, setCreds] = useState<KvRow[]>([{ key: '', value: '' }]);
  const [config, setConfig] = useState<KvRow[]>([{ key: '', value: '' }]);
  const [formError, setFormError] = useState<string | null>(null);

  const resetForm = () => {
    setName('');
    setChannel('webhook');
    setCreds([{ key: '', value: '' }]);
    setConfig([{ key: '', value: '' }]);
    setFormError(null);
  };

  const submit = () => {
    setFormError(null);
    create.mutate(
      {
        name: name.trim(),
        channel,
        credentials: kvToObject(creds),
        config: kvToObject(config),
      },
      {
        onSuccess: () => {
          setShowAdd(false);
          resetForm();
        },
        onError: (e) =>
          setFormError(
            isApiError(e) ? e.message : 'Could not create the target.',
          ),
      },
    );
  };

  const setRow = (
    rows: KvRow[],
    setRows: (r: KvRow[]) => void,
    i: number,
    patch: Partial<KvRow>,
  ) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r));
    // Keep a trailing empty row so there's always a place to add the next pair.
    if (i === rows.length - 1 && (patch.key || patch.value)) {
      next.push({ key: '', value: '' });
    }
    setRows(next);
  };

  const inputStyle = [
    styles.input,
    {
      backgroundColor: theme.colors.bg.card,
      borderColor: theme.colors.border.default,
      color: theme.colors.text.primary,
    },
  ];

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="caption" color="brand">
          PUBLISHING
        </Text>
        <Spacer size={2} />
        <Text variant="display">Targets</Text>
        <Spacer size={2} />
        <Text variant="body" color="secondary">
          Channels an approved draft can be delivered to.
        </Text>
        <Spacer size={4} />
        <Button
          label="Add target"
          variant="primary"
          fullWidth
          onPress={() => {
            resetForm();
            setShowAdd(true);
          }}
        />
        <Spacer size={6} />

        {targets.isLoading ? (
          <Skeleton height={72} />
        ) : (targets.data ?? []).length === 0 ? (
          <Card variant="default">
            <Text variant="body" color="secondary">
              No targets yet. Add one to start publishing.
            </Text>
          </Card>
        ) : (
          (targets.data ?? []).map((t) => (
            <View key={t.id}>
              <Card variant="default">
                <View style={styles.row}>
                  <View style={{ flex: 1 }}>
                    <View style={styles.badgeRow}>
                      <ChannelBadge channel={t.channel} />
                    </View>
                    <Spacer size={1} />
                    <Text variant="body">{t.name}</Text>
                    <Spacer size={1} />
                    <Text variant="caption" color="tertiary">
                      {t.lastHealthAt
                        ? `Health: ${t.lastHealthOk ? 'OK' : 'failing'}`
                        : 'Health: not checked'}
                    </Text>
                  </View>
                </View>
                <Spacer size={2} />
                <View style={styles.actions}>
                  <View style={styles.actionBtn}>
                    <Button
                      label="Check"
                      variant="secondary"
                      fullWidth
                      loading={health.isPending && health.variables === t.id}
                      onPress={() => health.mutate(t.id)}
                    />
                  </View>
                  <View style={styles.actionBtn}>
                    <Button
                      label="Delete"
                      variant="ghost"
                      fullWidth
                      onPress={() => remove.mutate(t.id)}
                    />
                  </View>
                </View>
              </Card>
              <Spacer size={2} />
            </View>
          ))
        )}
        <Spacer size={8} />
      </ScrollView>

      <Modal
        visible={showAdd}
        transparent
        animationType="slide"
        onRequestClose={() => setShowAdd(false)}
      >
        <View style={styles.sheetOverlay}>
          <View style={[styles.sheet, { backgroundColor: theme.colors.bg.elevated }]}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text variant="h2">Add target</Text>
              <Spacer size={3} />
              <Text variant="caption" color="tertiary">
                NAME
              </Text>
              <Spacer size={1} />
              <TextInput
                style={inputStyle}
                placeholder="My channel"
                placeholderTextColor={theme.colors.text.tertiary}
                value={name}
                onChangeText={setName}
              />
              <Spacer size={3} />
              <Text variant="caption" color="tertiary">
                CHANNEL
              </Text>
              <Spacer size={2} />
              <View style={styles.chips}>
                {CHANNELS.map((c) => {
                  const sel = c === channel;
                  return (
                    <Pressable key={c} onPress={() => setChannel(c)}>
                      <View
                        style={[
                          styles.chip,
                          {
                            borderColor: sel
                              ? theme.colors.semantic.positiveText
                              : theme.colors.border.subtle,
                            backgroundColor: sel
                              ? theme.colors.accent.tealGlow
                              : undefined,
                          },
                        ]}
                      >
                        <Text variant="caption" color={sel ? 'primary' : 'secondary'}>
                          {CHANNEL_LABEL[c]}
                        </Text>
                      </View>
                    </Pressable>
                  );
                })}
              </View>

              <Spacer size={3} />
              <Text variant="caption" color="tertiary">
                CREDENTIALS (write-only)
              </Text>
              <Spacer size={2} />
              {creds.map((r, i) => (
                <View key={`c-${i}`} style={styles.kvRow}>
                  <TextInput
                    style={[inputStyle, styles.kvKey]}
                    placeholder="key"
                    placeholderTextColor={theme.colors.text.tertiary}
                    value={r.key}
                    autoCapitalize="none"
                    onChangeText={(v) => setRow(creds, setCreds, i, { key: v })}
                  />
                  <TextInput
                    style={[inputStyle, styles.kvVal]}
                    placeholder="value"
                    placeholderTextColor={theme.colors.text.tertiary}
                    value={r.value}
                    autoCapitalize="none"
                    secureTextEntry
                    onChangeText={(v) => setRow(creds, setCreds, i, { value: v })}
                  />
                </View>
              ))}

              <Spacer size={3} />
              <Text variant="caption" color="tertiary">
                CONFIG
              </Text>
              <Spacer size={2} />
              {config.map((r, i) => (
                <View key={`f-${i}`} style={styles.kvRow}>
                  <TextInput
                    style={[inputStyle, styles.kvKey]}
                    placeholder="key"
                    placeholderTextColor={theme.colors.text.tertiary}
                    value={r.key}
                    autoCapitalize="none"
                    onChangeText={(v) => setRow(config, setConfig, i, { key: v })}
                  />
                  <TextInput
                    style={[inputStyle, styles.kvVal]}
                    placeholder="value"
                    placeholderTextColor={theme.colors.text.tertiary}
                    value={r.value}
                    autoCapitalize="none"
                    onChangeText={(v) => setRow(config, setConfig, i, { value: v })}
                  />
                </View>
              ))}

              {formError ? (
                <>
                  <Spacer size={2} />
                  <Text variant="caption" color="danger">
                    {formError}
                  </Text>
                </>
              ) : null}

              <Spacer size={4} />
              <Button
                label="Create"
                variant="primary"
                fullWidth
                loading={create.isPending}
                disabled={!name.trim()}
                onPress={submit}
              />
              <Spacer size={2} />
              <Button
                label="Cancel"
                variant="secondary"
                fullWidth
                onPress={() => setShowAdd(false)}
              />
              <Spacer size={4} />
            </ScrollView>
          </View>
        </View>
      </Modal>
    </Screen>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  badgeRow: { flexDirection: 'row' },
  actions: { flexDirection: 'row', gap: 8 },
  actionBtn: { flex: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  kvRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  kvKey: { flex: 1 },
  kvVal: { flex: 2 },
  sheet: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '88%',
    padding: 24,
    paddingBottom: 24,
  },
  sheetOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
});
