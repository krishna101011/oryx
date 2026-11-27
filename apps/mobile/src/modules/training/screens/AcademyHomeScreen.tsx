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
import {
  academyQueryState,
  courseCatalogState,
} from '../home';
import { useCourseCatalog, useCourseProgress, useEnrollInCourse } from '../hooks/useTraining';

/**
 * Academy course list (Phase 8 Wave C) — replaces TrainingHomeScreen's
 * Phase-1 placeholder. The catalog, enrollment, course progress and lesson
 * content are backed by real API calls. Video playback and course authoring
 * remain explicit follow-on integrations; this learner screen never
 * presents either as available when it is not.
 */
export const AcademyHomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const catalog = useCourseCatalog();
  const catalogState = courseCatalogState(catalog.data, catalog.isError);

  return (
    <Screen background="primary">
      <ScrollView showsVerticalScrollIndicator={false}>
        <Spacer size={6} />
        <Text variant="pageTitle">Academy</Text>
        <Spacer size={4} />

        {catalogState === 'loading' ? (
          <Card header={<CardHeader title="Courses" />}>
            <HairlineRowList>
              <SkeletonRow leadingWidth={56} hasTrailingChip />
              <SkeletonRow leadingWidth={56} hasTrailingChip />
              <SkeletonRow leadingWidth={56} hasTrailingChip />
            </HairlineRowList>
          </Card>
        ) : catalogState === 'error' ? (
          <Card header={<CardHeader title="Courses" />}>
            <Text variant="bodySm" color="secondary">
              We couldn't load the Academy catalog. Check your connection and try again.
            </Text>
            <Spacer size={3} />
            <Button
              label="Try again"
              variant="secondary"
              onPress={() => { void catalog.refetch(); }}
            />
          </Card>
        ) : catalogState === 'empty' ? (
          <EmptyState
            icon="horn"
            title="No courses yet"
            description="The Academy catalog is currently empty. Courses will appear here when they are published."
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
  // Fetch lesson progress only after an enrolled course is expanded.
  const progress = useCourseProgress(course.id, expanded);
  const progressState = academyQueryState(progress.data, progress.isError);

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
      {!course.enrolled && enroll.isError ? (
        <View style={styles.message}>
          <Text variant="caption" color="secondary">
            We couldn't enroll you in this course. Please try again.
          </Text>
        </View>
      ) : null}
      {expanded && course.enrolled ? (
        <View style={styles.lessonsBlock}>
          {progressState === 'loading' ? (
            <SkeletonRow leadingWidth={0} hasChevron={false} />
          ) : progressState === 'error' ? (
            <View>
              <Text variant="bodySm" color="secondary">
                We couldn't load this course's lessons. Please try again.
              </Text>
              <Spacer size={2} />
              <Button
                label="Try again"
                variant="secondary"
                onPress={() => { void progress.refetch(); }}
              />
            </View>
          ) : (progress.data?.lessons ?? []).length === 0 ? (
            <Text variant="bodySm" color="tertiary">
              No lessons have been published for this course yet.
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
  message: { paddingTop: 4 },
  certificateBanner: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
});
