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
import { academyQueryState } from '../home';
import { useCompleteLesson, useLessonDetail } from '../hooks/useTraining';

/**
 * Lesson viewer (Phase 8 Wave C). Displays real lesson content and supports
 * marking a lesson complete. Video playback remains unavailable until the
 * Cloudflare Stream credentials and playback flow are configured.
 */
export const LessonViewerScreen: React.FC = () => {
  const t = useTheme();
  const route = useRoute<RouteProp<AcademyStackParamList, 'LessonViewer'>>();
  const { lessonId } = route.params;
  const lesson = useLessonDetail(lessonId);
  // courseId comes from the lesson's own response, not the route.
  const complete = useCompleteLesson(lessonId, lesson.data?.courseId ?? '');
  const lessonState = academyQueryState(lesson.data, lesson.isError);

  if (lessonState === 'loading') {
    return (
      <Screen background="primary">
        <View style={styles.center}>
          <ActivityIndicator color={t.colors.accent.amber} />
        </View>
      </Screen>
    );
  }

  if (lessonState === 'error') {
    return (
      <Screen background="primary">
        <ScrollView showsVerticalScrollIndicator={false}>
          <Spacer size={6} />
          <Card>
            <Text variant="bodySm" color="secondary">
              We couldn't load this lesson. Check your connection and try again.
            </Text>
            <Spacer size={3} />
            <Button
              label="Try again"
              variant="secondary"
              onPress={() => { void lesson.refetch(); }}
            />
          </Card>
        </ScrollView>
      </Screen>
    );
  }

  const data = lesson.data!;
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
                This lesson has a video, but real playback isn't configured yet.
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
          <>
            {complete.isError ? (
              <>
                <Text variant="bodySm" color="secondary">
                  We couldn't save your completion. Please try again.
                </Text>
                <Spacer size={2} />
              </>
            ) : null}
            <Button
              label={complete.isError ? 'Try again' : 'Mark complete'}
              variant="primary"
              fullWidth
              disabled={complete.isPending}
              onPress={() => complete.mutate()}
            />
          </>
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
