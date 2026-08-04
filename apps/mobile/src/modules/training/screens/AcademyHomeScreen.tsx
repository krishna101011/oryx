import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { Training } from '@oryx/shared-types';
import {
  Button,
  Card,
  CardHeader,
  HairlineRowList,
  Icon,
  Screen,
  SkeletonRow,
  Spacer,
  Text,
} from '@oryx/design-system';
import { EmptyState } from '../../../components/EmptyState';
import { useCourseCatalog, useCourseProgress, useEnrollInCourse } from '../hooks/useTraining';

/**
 * Academy course list (Phase 8 Wave C) — replaces TrainingHomeScreen's
 * Phase-1 placeholder. Follows ResearchWorkspaceListScreen.tsx's confirmed
 * hook-wrapped useQuery + Card/CardHeader/HairlineRowList pattern exactly
 * (recon, this wave). Real catalog, real per-course enrollment status, a
 * real enroll action. Expanding an enrolled course fetches its real
 * progress and lists real lessons — tapping one opens the lesson viewer.
 * No video player anywhere on this screen; that honest boundary lives in
 * LessonViewerScreen.
 */
export const AcademyHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const catalog = useCourseCatalog();

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Academy</Text>
        <Spacer size={4} />

        {catalog.isLoading ? (
          <Card header={<CardHeader title="Courses" />}>
            <HairlineRowList>
              <SkeletonRow leadingWidth={56} hasTrailingChip />
              <SkeletonRow leadingWidth={56} hasTrailingChip />
              <SkeletonRow leadingWidth={56} hasTrailingChip />
            </HairlineRowList>
          </Card>
        ) : (catalog.data ?? []).length === 0 ? (
          <EmptyState
            icon="horn"
            title="No courses yet"
            description="Real courses will appear here once the Academy catalog has content."
          />
        ) : (
          <Card
            header={
              <CardHeader
                title="Courses"
                sub={`${catalog.data!.length} AVAILABLE`}
              />
            }
          >
            <HairlineRowList>
              {catalog.data!.map((course) => (
                <CourseRow
                  key={course.id}
                  course={course}
                  onOpenLesson={(lessonId) =>
                    // @ts-expect-error cross-stack navigate, same convention
                    // as ResearchWorkspaceListScreen's WorkspaceCard press.
                    navigation.navigate('LessonViewer', { lessonId })
                  }
                />
              ))}
            </HairlineRowList>
          </Card>
        )}
        <Spacer size={8} />
      </ScrollView>
    </Screen>
  );
};

const CourseRow: React.FC<{
  course: Training.CourseCatalogItem;
  onOpenLesson: (lessonId: string) => void;
}> = ({ course, onOpenLesson }) => {
  const [expanded, setExpanded] = useState(false);
  const enroll = useEnrollInCourse();
  // Only fetch progress once the learner has actually opened the course —
  // no point loading lesson data for every collapsed row on the screen.
  const progress = useCourseProgress(course.id);

  return (
    <View>
      <Pressable
        onPress={() => course.enrolled && setExpanded((v) => !v)}
        accessibilityRole="button"
        accessibilityLabel={`${course.title} — ${course.enrolled ? (expanded ? 'hide lessons' : 'show lessons') : 'not enrolled'}`}
      >
        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text variant="body">{course.title}</Text>
            {course.description ? (
              <>
                <Spacer size={1} />
                <Text variant="bodySm" color="secondary">
                  {course.description}
                </Text>
              </>
            ) : null}
          </View>
          {course.enrolled ? (
            <>
              <View style={styles.enrolledChip}>
                <Text variant="caption" color="brand">
                  ENROLLED
                </Text>
              </View>
              <Icon name={expanded ? 'ChevronUp' : 'ChevronDown'} size="sm" color="tertiary" />
            </>
          ) : (
            <Button
              label="Enroll"
              variant="secondary"
              disabled={enroll.isPending}
              onPress={() => enroll.mutate(course.id)}
            />
          )}
        </View>
      </Pressable>
      {expanded && course.enrolled ? (
        <View style={styles.lessonsBlock}>
          {progress.isLoading ? (
            <SkeletonRow leadingWidth={0} hasChevron={false} />
          ) : (progress.data?.lessons ?? []).length === 0 ? (
            <Text variant="bodySm" color="tertiary">
              No lessons yet.
            </Text>
          ) : (
            progress.data!.lessons.map((lesson) => (
              <Pressable
                key={lesson.lessonId}
                onPress={() => onOpenLesson(lesson.lessonId)}
                accessibilityRole="button"
                accessibilityLabel={lesson.title}
                style={styles.lessonRow}
              >
                <Icon
                  name={lesson.completed ? 'CheckCircle' : 'Circle'}
                  size="sm"
                  color={lesson.completed ? 'brand' : 'tertiary'}
                />
                <Spacer size={2} axis="horizontal" />
                <Text variant="bodySm" style={{ flex: 1 }}>
                  {lesson.title}
                </Text>
                {lesson.hasVideo ? (
                  <Icon name="Play" size="sm" color="tertiary" />
                ) : null}
              </Pressable>
            ))
          )}
          {progress.data?.certificate ? (
            <>
              <Spacer size={2} />
              <View style={styles.certificateBanner}>
                <Icon name="Award" size="sm" color="brand" />
                <Spacer size={2} axis="horizontal" />
                <Text variant="bodySm" color="brand">
                  Certificate earned
                </Text>
              </View>
            </>
          ) : null}
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  enrolledChip: { paddingHorizontal: 8, paddingVertical: 2 },
  lessonsBlock: { paddingLeft: 8, paddingTop: 8 },
  lessonRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  certificateBanner: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
});
