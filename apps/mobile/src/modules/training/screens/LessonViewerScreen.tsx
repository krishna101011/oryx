import React from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { type RouteProp, useRoute } from '@react-navigation/native';
import {
  Button,
  Card,
  Icon,
  Screen,
  Spacer,
  Text,
  useTheme,
} from '@oryx/design-system';
import type { AcademyStackParamList } from '../../../navigation/types';
import { useCompleteLesson, useLessonDetail } from '../hooks/useTraining';

/**
 * Lesson viewer (Phase 8 Wave C). Real title, real transcript, a real
 * mark-complete action — and, where video would play, an honest, clearly
 * labeled "Video not yet available" state, never a broken or fake player.
 * Recon (this wave) confirmed no endpoint anywhere resolves a real
 * Cloudflare playback URL — this screen never attempts one; hasVideo only
 * decides which of the two states below renders.
 */
export const LessonViewerScreen: React.FC = () => {
  const t = useTheme();
  const route = useRoute<RouteProp<AcademyStackParamList, 'LessonViewer'>>();
  const { lessonId } = route.params;
  const lesson = useLessonDetail(lessonId);
  // courseId comes from the lesson's own response, not the route — see
  // AcademyStackParamList's LessonViewer comment. useCompleteLesson is only
  // ever invoked (via the Mark complete button below) once lesson.data is
  // loaded, so the '' fallback here is never actually used.
  const complete = useCompleteLesson(lessonId, lesson.data?.courseId ?? '');

  if (lesson.isLoading || !lesson.data) {
    return (
      <Screen background="primary">
        <View style={styles.center}>
          <ActivityIndicator color={t.colors.accent.amber} />
        </View>
      </Screen>
    );
  }

  const data = lesson.data;
  const justIssuedCertificate = complete.data?.certificate ?? null;

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">{data.title}</Text>
        <Spacer size={4} />

        {data.hasVideo ? (
          <Card variant="elevated">
            <View style={styles.videoPlaceholder}>
              <Icon name="VideoOff" size="lg" color="tertiary" />
              <Spacer size={2} />
              <Text variant="body" color="secondary" align="center">
                Video not yet available
              </Text>
              <Spacer size={1} />
              <Text variant="caption" color="tertiary" align="center">
                This lesson has a video, but real playback isn't wired up yet.
              </Text>
            </View>
          </Card>
        ) : null}

        <Spacer size={4} />
        {data.transcriptText ? (
          <Card>
            <Text variant="body">{data.transcriptText}</Text>
          </Card>
        ) : (
          <Text variant="bodySm" color="tertiary">
            No transcript yet for this lesson.
          </Text>
        )}

        <Spacer size={6} />
        {data.completed ? (
          <View style={styles.completedRow}>
            <Icon name="CheckCircle" size="sm" color="brand" />
            <Spacer size={2} axis="horizontal" />
            <Text variant="bodySm" color="brand">
              Completed
            </Text>
          </View>
        ) : (
          <Button
            label="Mark complete"
            variant="primary"
            fullWidth
            disabled={complete.isPending}
            onPress={() => complete.mutate()}
          />
        )}

        {justIssuedCertificate ? (
          <>
            <Spacer size={4} />
            <Card variant="elevated">
              <View style={styles.certificateRow}>
                <Icon name="Award" size="lg" color="brand" />
                <Spacer size={2} axis="horizontal" />
                <View style={{ flex: 1 }}>
                  <Text variant="body" color="brand">
                    Certificate earned
                  </Text>
                  <Text variant="caption" color="tertiary">
                    You completed every lesson in this course.
                  </Text>
                </View>
              </View>
            </Card>
          </>
        ) : null}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  videoPlaceholder: { alignItems: 'center', paddingVertical: 24 },
  completedRow: { flexDirection: 'row', alignItems: 'center' },
  certificateRow: { flexDirection: 'row', alignItems: 'center' },
});
