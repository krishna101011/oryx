import React, { useEffect, useRef, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useRoute } from '@react-navigation/native';
import {
  Button,
  Card,
  Screen,
  Skeleton,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { ContentFormat, ContentTemplate } from '@oryx/shared-types';
import {
  useApproveDraft,
  useDraft,
  useDraftVersions,
  useRegenerateDraft,
  useRejectDraft,
  useRequestChanges,
  useSaveVersion,
  useSubmitReview,
  useSwitchFormat,
} from '../hooks/useDrafts';
import type { PublishTargetResult } from '@oryx/shared-types';
import { FormatBadge } from '../components/FormatBadge';
import { DraftStatusPill } from '../components/DraftStatusPill';
import { CitationTag } from '../components/CitationTag';
import { ChannelBadge } from '../components/ChannelBadge';
import { VersionHistoryList } from '../components/VersionHistoryList';
import { TemplatePicker } from '../components/TemplatePicker';
import { CONTENT_FORMATS, FORMAT_LABEL } from '../theme/draftColors';
import { usePublishDraft, useTargets } from '../hooks/usePublishing';
import { useScheduleDraft } from '../hooks/useCalendar';
import { isApiError } from '../../../lib/errors';

// Quick presets for the "Schedule for later" picker — dependency-free, web-safe.
const SCHEDULE_PRESETS: { label: string; offsetMs: number }[] = [
  { label: 'In 1 hour', offsetMs: 60 * 60 * 1000 },
  { label: 'In 4 hours', offsetMs: 4 * 60 * 60 * 1000 },
  { label: 'Tomorrow', offsetMs: 24 * 60 * 60 * 1000 },
  { label: 'Next week', offsetMs: 7 * 24 * 60 * 60 * 1000 },
];

type ReviewAction = 'approve' | 'reject' | 'request_changes';

const REVIEW_ACTION_LABEL: Record<ReviewAction, string> = {
  approve: 'Approve',
  reject: 'Reject',
  request_changes: 'Request Changes',
};

// Note is required for reject / request-changes, optional for approve —
// mirrors the backend's exact contract (Wave C Refinement 1).
const NOTE_REQUIRED: Record<ReviewAction, boolean> = {
  approve: false,
  reject: true,
  request_changes: true,
};

export const DraftEditorScreen: React.FC = () => {
  const route = useRoute();
  const { draftId } = route.params as { draftId: string };
  const theme = useTheme();

  const draft = useDraft(draftId);
  const versions = useDraftVersions(draftId);
  const save = useSaveVersion(draftId);
  const regen = useRegenerateDraft(draftId);
  const switchFmt = useSwitchFormat(draftId);
  const submitReview = useSubmitReview(draftId);
  const approve = useApproveDraft(draftId);
  const reject = useRejectDraft(draftId);
  const requestChanges = useRequestChanges(draftId);

  const [content, setContent] = useState('');
  const loadedVersion = useRef<number | null>(null);
  const [showSwitchSheet, setShowSwitchSheet] = useState(false);
  const [switchFormat, setSwitchFormat] = useState<ContentFormat>('article');
  const [switchTemplate, setSwitchTemplate] = useState<ContentTemplate | null>(null);

  // Review-action note sheet (Wave C). `reviewAction === null` → closed.
  const [reviewAction, setReviewAction] = useState<ReviewAction | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewError, setReviewError] = useState<string | null>(null);

  const reviewPending =
    approve.isPending || reject.isPending || requestChanges.isPending;

  // Wave D — publish (only when status === 'approved').
  const targets = useTargets();
  const publish = usePublishDraft(draftId);
  const [showPublish, setShowPublish] = useState(false);
  const [selectedTargets, setSelectedTargets] = useState<Set<string>>(new Set());
  const [publishResults, setPublishResults] = useState<PublishTargetResult[] | null>(
    null,
  );

  const toggleTarget = (id: string) =>
    setSelectedTargets((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const runPublish = () => {
    setPublishResults(null);
    publish.mutate(Array.from(selectedTargets), {
      onSuccess: (results) => setPublishResults(results),
    });
  };

  // Wave E — schedule for later (one target + future time).
  const schedule = useScheduleDraft(draftId);
  const [showSchedule, setShowSchedule] = useState(false);
  const [scheduleTarget, setScheduleTarget] = useState<string | null>(null);
  const [scheduleAtIso, setScheduleAtIso] = useState<string>('');
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [scheduleDone, setScheduleDone] = useState(false);

  const openSchedule = () => {
    setScheduleTarget(null);
    setScheduleError(null);
    setScheduleDone(false);
    // Default to one hour out so the field is never empty / in the past.
    setScheduleAtIso(new Date(Date.now() + 60 * 60 * 1000).toISOString());
    setShowSchedule(true);
  };

  const runSchedule = () => {
    setScheduleError(null);
    if (!scheduleTarget) {
      setScheduleError('Select a target.');
      return;
    }
    const when = new Date(scheduleAtIso);
    if (Number.isNaN(when.getTime()) || when.getTime() <= Date.now()) {
      setScheduleError('Pick a valid future time.');
      return;
    }
    schedule.mutate(
      {
        draft_id: draftId,
        target_id: scheduleTarget,
        scheduled_at: when.toISOString(),
      },
      {
        onSuccess: () => setScheduleDone(true),
        onError: (e) =>
          setScheduleError(
            isApiError(e) ? e.message : 'Could not schedule. Try again.',
          ),
      },
    );
  };

  const openReview = (action: ReviewAction) => {
    setReviewAction(action);
    setReviewNote('');
    setReviewError(null);
  };

  const submitReviewAction = () => {
    if (!reviewAction) return;
    const note = reviewNote.trim();
    setReviewError(null);
    const onError = (e: unknown) => {
      // Show the real backend message (e.g. the self-approval rejection),
      // matching the signup/login error-display pattern.
      setReviewError(
        isApiError(e) ? e.message : 'Something went wrong. Try again.',
      );
    };
    const onSuccess = () => setReviewAction(null);
    if (reviewAction === 'approve') {
      approve.mutate(note ? { note } : {}, { onSuccess, onError });
    } else if (reviewAction === 'reject') {
      reject.mutate({ note }, { onSuccess, onError });
    } else {
      requestChanges.mutate({ note }, { onSuccess, onError });
    }
  };

  // Re-seed the editor whenever a new current version lands (generate,
  // regenerate, or save bumps currentVersion). Edits in between are preserved.
  useEffect(() => {
    const d = draft.data;
    if (!d) return;
    if (loadedVersion.current !== d.currentVersion) {
      setContent(d.currentContent ?? '');
      loadedVersion.current = d.currentVersion;
    }
  }, [draft.data]);

  if (draft.isLoading || !draft.data) {
    return (
      <Screen background="primary">
        <Spacer size={6} />
        <Skeleton height={220} />
      </Screen>
    );
  }

  const d = draft.data;
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={4} />
        <View style={styles.headerRow}>
          <FormatBadge format={d.format} />
          <DraftStatusPill status={d.status} />
        </View>
        <Spacer size={2} />
        <Text variant="h2">{d.title}</Text>
        <Spacer size={1} />
        <Text variant="caption" color="tertiary">
          {wordCount} words · v{d.currentVersion} · {d.generationModel}
        </Text>

        <Spacer size={4} />
        <Text variant="bodySm" color="secondary">
          Citations
        </Text>
        <Spacer size={2} />
        <View style={styles.citations}>
          {d.citationObjectIds.length === 0 ? (
            <Text variant="caption" color="tertiary">
              No citations.
            </Text>
          ) : (
            d.citationObjectIds.map((id) => (
              <CitationTag key={id} label={id.slice(0, 8)} />
            ))
          )}
        </View>
        <Spacer size={1} />
        <Text variant="caption" color="tertiary">
          These sources will be included automatically when published.
        </Text>

        <Spacer size={4} />
        <TextInput
          value={content}
          onChangeText={setContent}
          multiline
          placeholder="Draft content…"
          placeholderTextColor={theme.colors.text.tertiary}
          style={[
            styles.editor,
            {
              color: theme.colors.text.primary,
              borderColor: theme.colors.border.subtle,
            },
          ]}
        />

        <Spacer size={4} />
        <Button
          label="Save version"
          variant="primary"
          fullWidth
          loading={save.isPending}
          disabled={!content.trim()}
          onPress={() => save.mutate({ content })}
        />
        <Spacer size={2} />
        <Button
          label="Regenerate with AI"
          variant="secondary"
          fullWidth
          loading={regen.isPending}
          onPress={() => regen.mutate({})}
        />
        <Spacer size={2} />
        <Button
          label="Switch Format"
          variant="secondary"
          fullWidth
          loading={switchFmt.isPending}
          onPress={() => {
            setSwitchFormat(d.format as ContentFormat);
            setSwitchTemplate(null);
            setShowSwitchSheet(true);
          }}
        />

        {/* Wave C — submit for review (only from 'draft'). */}
        {d.status === 'draft' && (
          <>
            <Spacer size={2} />
            <Button
              label="Submit for Review"
              variant="primary"
              fullWidth
              loading={submitReview.isPending}
              disabled={!content.trim()}
              onPress={() => submitReview.mutate()}
            />
          </>
        )}

        {/* Wave D — publish + Wave E — schedule (once 'approved'). */}
        {d.status === 'approved' && (
          <>
            <Spacer size={2} />
            <Button
              label="Publish"
              variant="primary"
              fullWidth
              onPress={() => {
                setSelectedTargets(new Set());
                setPublishResults(null);
                setShowPublish(true);
              }}
            />
            <Spacer size={2} />
            <Button
              label="Schedule for later"
              variant="secondary"
              fullWidth
              onPress={openSchedule}
            />
          </>
        )}

        {/* Wave E — a scheduled draft can schedule additional targets. */}
        {d.status === 'scheduled' && (
          <>
            <Spacer size={2} />
            <Button
              label="Schedule another target"
              variant="secondary"
              fullWidth
              onPress={openSchedule}
            />
          </>
        )}

        {/* Wave C — reviewer actions (only while 'in_review'). */}
        {d.status === 'in_review' && (
          <>
            <Spacer size={4} />
            <Text variant="bodySm" color="secondary">
              Reviewer actions
            </Text>
            <Spacer size={2} />
            <Button
              label="Approve"
              variant="primary"
              fullWidth
              onPress={() => openReview('approve')}
            />
            <Spacer size={2} />
            <Button
              label="Request Changes"
              variant="secondary"
              fullWidth
              onPress={() => openReview('request_changes')}
            />
            <Spacer size={2} />
            <Button
              label="Reject"
              variant="secondary"
              fullWidth
              onPress={() => openReview('reject')}
            />
          </>
        )}

        <Modal
          visible={showSwitchSheet}
          transparent
          animationType="slide"
          onRequestClose={() => setShowSwitchSheet(false)}
        >
          <View style={styles.sheetOverlay}>
            <View
              style={[
                styles.sheet,
                { backgroundColor: theme.colors.bg.elevated },
              ]}
            >
              <Text variant="h2">Switch Format</Text>
              <Spacer size={3} />
              <View style={styles.chips}>
                {CONTENT_FORMATS.map((f) => {
                  const sel = f === switchFormat;
                  return (
                    <Pressable
                      key={f}
                      onPress={() => {
                        setSwitchFormat(f);
                        setSwitchTemplate(null);
                      }}
                    >
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
                          {FORMAT_LABEL[f]}
                        </Text>
                      </View>
                    </Pressable>
                  );
                })}
              </View>
              <TemplatePicker
                format={switchFormat}
                selectedId={switchTemplate?.id ?? null}
                onSelect={setSwitchTemplate}
              />
              <Spacer size={4} />
              <Button
                label="Switch & Regenerate"
                variant="primary"
                fullWidth
                loading={switchFmt.isPending}
                onPress={() => {
                  switchFmt.mutate(
                    { format: switchFormat, template_id: switchTemplate?.id ?? null },
                    { onSuccess: () => setShowSwitchSheet(false) },
                  );
                }}
              />
              <Spacer size={2} />
              <Button
                label="Cancel"
                variant="secondary"
                fullWidth
                onPress={() => setShowSwitchSheet(false)}
              />
            </View>
          </View>
        </Modal>

        {/* Wave C — review-action note sheet. */}
        <Modal
          visible={reviewAction !== null}
          transparent
          animationType="slide"
          onRequestClose={() => setReviewAction(null)}
        >
          <View style={styles.sheetOverlay}>
            <View
              style={[styles.sheet, { backgroundColor: theme.colors.bg.elevated }]}
            >
              <Text variant="h2">
                {reviewAction ? REVIEW_ACTION_LABEL[reviewAction] : ''}
              </Text>
              <Spacer size={2} />
              <Text variant="caption" color="tertiary">
                {reviewAction && NOTE_REQUIRED[reviewAction]
                  ? 'A note is required.'
                  : 'Add an optional note.'}
              </Text>
              <Spacer size={3} />
              <TextInput
                value={reviewNote}
                onChangeText={setReviewNote}
                multiline
                placeholder="Note…"
                placeholderTextColor={theme.colors.text.tertiary}
                style={[
                  styles.noteInput,
                  {
                    color: theme.colors.text.primary,
                    borderColor: theme.colors.border.subtle,
                  },
                ]}
              />
              {reviewError ? (
                <>
                  <Spacer size={2} />
                  <Text variant="caption" color="danger">
                    {reviewError}
                  </Text>
                </>
              ) : null}
              <Spacer size={4} />
              <Button
                label={reviewAction ? REVIEW_ACTION_LABEL[reviewAction] : 'Submit'}
                variant="primary"
                fullWidth
                loading={reviewPending}
                disabled={
                  !!reviewAction &&
                  NOTE_REQUIRED[reviewAction] &&
                  !reviewNote.trim()
                }
                onPress={submitReviewAction}
              />
              <Spacer size={2} />
              <Button
                label="Cancel"
                variant="secondary"
                fullWidth
                onPress={() => setReviewAction(null)}
              />
            </View>
          </View>
        </Modal>

        {/* Wave D — target picker + per-target results. */}
        <Modal
          visible={showPublish}
          transparent
          animationType="slide"
          onRequestClose={() => setShowPublish(false)}
        >
          <View style={styles.sheetOverlay}>
            <View style={[styles.sheet, { backgroundColor: theme.colors.bg.elevated }]}>
              <Text variant="h2">Publish</Text>
              <Spacer size={2} />
              <Text variant="caption" color="tertiary">
                Select the targets to deliver to.
              </Text>
              <Spacer size={3} />
              {(targets.data ?? []).filter((t) => t.isActive).length === 0 ? (
                <Text variant="bodySm" color="secondary">
                  No active targets. Add one under Publish targets first.
                </Text>
              ) : (
                (targets.data ?? [])
                  .filter((t) => t.isActive)
                  .map((t) => {
                    const sel = selectedTargets.has(t.id);
                    return (
                      <Pressable key={t.id} onPress={() => toggleTarget(t.id)}>
                        <View
                          style={[
                            styles.targetRow,
                            {
                              borderColor: sel
                                ? theme.colors.semantic.positiveText
                                : theme.colors.border.subtle,
                            },
                          ]}
                        >
                          <ChannelBadge channel={t.channel} />
                          <Text variant="body" color={sel ? 'primary' : 'secondary'}>
                            {t.name}
                          </Text>
                          <Text variant="caption" color={sel ? 'brand' : 'tertiary'}>
                            {sel ? 'Selected' : 'Tap to select'}
                          </Text>
                        </View>
                      </Pressable>
                    );
                  })
              )}

              {publishResults ? (
                <>
                  <Spacer size={3} />
                  <Text variant="bodySm" color="secondary">
                    Results
                  </Text>
                  <Spacer size={2} />
                  {publishResults.map((r) => (
                    <Text
                      key={r.targetId}
                      variant="caption"
                      color={r.status === 'delivered' ? 'brand' : 'danger'}
                    >
                      {r.status.toUpperCase()}
                      {r.errorMessage ? ` — ${r.errorMessage}` : ''}
                    </Text>
                  ))}
                </>
              ) : null}

              <Spacer size={4} />
              <Button
                label="Publish now"
                variant="primary"
                fullWidth
                loading={publish.isPending}
                disabled={selectedTargets.size === 0}
                onPress={runPublish}
              />
              <Spacer size={2} />
              <Button
                label="Close"
                variant="secondary"
                fullWidth
                onPress={() => setShowPublish(false)}
              />
            </View>
          </View>
        </Modal>

        {/* Wave E — schedule-for-later sheet. */}
        <Modal
          visible={showSchedule}
          transparent
          animationType="slide"
          onRequestClose={() => setShowSchedule(false)}
        >
          <View style={styles.sheetOverlay}>
            <View style={[styles.sheet, { backgroundColor: theme.colors.bg.elevated }]}>
              <Text variant="h2">Schedule for later</Text>
              <Spacer size={2} />
              <Text variant="caption" color="tertiary">
                Pick a target and a future time. The scheduler publishes it then.
              </Text>
              <Spacer size={3} />

              {(targets.data ?? []).filter((t) => t.isActive).length === 0 ? (
                <Text variant="bodySm" color="secondary">
                  No active targets. Add one under Publish targets first.
                </Text>
              ) : (
                (targets.data ?? [])
                  .filter((t) => t.isActive)
                  .map((t) => {
                    const sel = scheduleTarget === t.id;
                    return (
                      <Pressable key={t.id} onPress={() => setScheduleTarget(t.id)}>
                        <View
                          style={[
                            styles.targetRow,
                            {
                              borderColor: sel
                                ? theme.colors.semantic.positiveText
                                : theme.colors.border.subtle,
                            },
                          ]}
                        >
                          <ChannelBadge channel={t.channel} />
                          <Text variant="body" color={sel ? 'primary' : 'secondary'}>
                            {t.name}
                          </Text>
                          <Text variant="caption" color={sel ? 'brand' : 'tertiary'}>
                            {sel ? 'Selected' : 'Tap to select'}
                          </Text>
                        </View>
                      </Pressable>
                    );
                  })
              )}

              <Spacer size={3} />
              <Text variant="bodySm" color="secondary">
                When
              </Text>
              <Spacer size={2} />
              <View style={styles.chips}>
                {SCHEDULE_PRESETS.map((p) => (
                  <Pressable
                    key={p.label}
                    onPress={() =>
                      setScheduleAtIso(new Date(Date.now() + p.offsetMs).toISOString())
                    }
                  >
                    <View
                      style={[
                        styles.chip,
                        { borderColor: theme.colors.border.subtle },
                      ]}
                    >
                      <Text variant="caption" color="secondary">
                        {p.label}
                      </Text>
                    </View>
                  </Pressable>
                ))}
              </View>
              <Spacer size={2} />
              <TextInput
                value={scheduleAtIso}
                onChangeText={setScheduleAtIso}
                placeholder="YYYY-MM-DDTHH:MM:SSZ"
                placeholderTextColor={theme.colors.text.tertiary}
                autoCapitalize="none"
                style={[
                  styles.noteInput,
                  {
                    color: theme.colors.text.primary,
                    borderColor: theme.colors.border.subtle,
                    minHeight: 44,
                  },
                ]}
              />

              {scheduleError ? (
                <>
                  <Spacer size={2} />
                  <Text variant="caption" color="danger">
                    {scheduleError}
                  </Text>
                </>
              ) : null}
              {scheduleDone ? (
                <>
                  <Spacer size={2} />
                  <Text variant="caption" color="brand">
                    Scheduled.
                  </Text>
                </>
              ) : null}

              <Spacer size={4} />
              <Button
                label="Schedule"
                variant="primary"
                fullWidth
                loading={schedule.isPending}
                disabled={!scheduleTarget}
                onPress={runSchedule}
              />
              <Spacer size={2} />
              <Button
                label="Close"
                variant="secondary"
                fullWidth
                onPress={() => setShowSchedule(false)}
              />
            </View>
          </View>
        </Modal>

        <Spacer size={6} />
        <Text variant="bodySm" color="secondary">
          Version history
        </Text>
        <Spacer size={2} />
        <Card variant="elevated">
          <VersionHistoryList versions={versions.data ?? []} />
        </Card>
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  citations: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  editor: {
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 220,
    padding: 12,
    textAlignVertical: 'top',
  },
  noteInput: {
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 90,
    padding: 12,
    textAlignVertical: 'top',
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'space-between',
  },
  sheet: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    paddingBottom: 40,
  },
  sheetOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  targetRow: {
    alignItems: 'center',
    borderRadius: 10,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 10,
    marginBottom: 8,
    padding: 12,
  },
});
