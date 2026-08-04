/**
 * Typed wrappers for Phase 8 Wave C's learner-facing training endpoints.
 * Course/Module/Lesson are platform-wide (no workspaceId) — see
 * docs/PHASE_8_TRAINING_ARCHITECTURE.md §2/§4. GET /training/catalog is
 * distinct from the admin-only GET /training/courses (authoring context) —
 * this is the real learner-facing course list, with per-course enrollment
 * status computed for the calling account.
 */
import type { Training } from '@oryx/shared-types';
import { apiClient } from '../../../lib/api/client';

export const trainingApi = {
  getCatalog: (): Promise<Training.CourseCatalogResponse> =>
    apiClient().get<Training.CourseCatalogResponse>('/training/catalog'),

  enroll: (courseId: string): Promise<Training.EnrollmentResult> =>
    apiClient().post<Training.EnrollmentResult>(
      `/training/courses/${courseId}/enroll`,
    ),

  getProgress: (courseId: string): Promise<Training.CourseProgress> =>
    apiClient().get<Training.CourseProgress>(
      `/training/courses/${courseId}/progress`,
    ),

  getLesson: (lessonId: string): Promise<Training.LessonDetail> =>
    apiClient().get<Training.LessonDetail>(`/training/lessons/${lessonId}`),

  completeLesson: (lessonId: string): Promise<Training.LessonCompleteResult> =>
    apiClient().post<Training.LessonCompleteResult>(
      `/training/lessons/${lessonId}/complete`,
    ),
};
