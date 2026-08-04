import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Training } from '@oryx/shared-types';
import { trainingApi } from '../api/training';

export function useCourseCatalog() {
  return useQuery<Training.CourseCatalogItem[]>({
    queryKey: ['training', 'catalog'],
    queryFn: async () => (await trainingApi.getCatalog()).courses,
  });
}

export function useEnrollInCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (courseId: string) => trainingApi.enroll(courseId),
    onSuccess: (_result, courseId) => {
      qc.invalidateQueries({ queryKey: ['training', 'catalog'] });
      qc.invalidateQueries({ queryKey: ['training', 'progress', courseId] });
    },
  });
}

export function useCourseProgress(courseId: string) {
  return useQuery<Training.CourseProgress>({
    queryKey: ['training', 'progress', courseId],
    queryFn: () => trainingApi.getProgress(courseId),
  });
}

export function useLessonDetail(lessonId: string) {
  return useQuery<Training.LessonDetail>({
    queryKey: ['training', 'lesson', lessonId],
    queryFn: () => trainingApi.getLesson(lessonId),
  });
}

export function useCompleteLesson(lessonId: string, courseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => trainingApi.completeLesson(lessonId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training', 'lesson', lessonId] });
      qc.invalidateQueries({ queryKey: ['training', 'progress', courseId] });
    },
  });
}
