/** Training/Academy domain types — Phase 8 Wave C (learner-facing frontend).
 *
 * Course/Module/Lesson are platform-wide (no workspaceId) — see
 * docs/PHASE_8_TRAINING_ARCHITECTURE.md §2/§4. Only the learner-facing
 * shapes this wave's mobile screens actually consume are mirrored here.
 * The raw video_asset_id is NEVER exposed to a learner (it's a meaningless
 * placeholder string today, not real Cloudflare data, per recon) — only
 * the derived hasVideo boolean crosses the wire. The is_platform_admin-
 * gated authoring endpoints have no frontend yet and stay as plain dicts
 * on the backend (services/training/router.py).
 */
import type { Id, Timestamp } from './common';

export interface CourseCatalogItem {
  id: Id;
  title: string;
  description: string | null;
  enrolled: boolean;
  enrolledAt: Timestamp | null;
}

export interface CourseCatalogResponse {
  courses: CourseCatalogItem[];
}

export interface EnrollmentResult {
  accountId: Id;
  courseId: Id;
  enrolledAt: Timestamp;
}

export interface LessonProgressResult {
  accountId: Id;
  lessonId: Id;
  completedAt: Timestamp;
}

export interface CertificateStatus {
  accountId: Id;
  courseId: Id;
  issuedAt: Timestamp;
}

export interface LessonSummary {
  lessonId: Id;
  moduleId: Id;
  title: string;
  hasVideo: boolean;
  completed: boolean;
  completedAt: Timestamp | null;
}

export interface CourseProgress {
  courseId: Id;
  enrollment: EnrollmentResult | null;
  lessons: LessonSummary[];
  certificate: CertificateStatus | null;
}

export interface LessonDetail {
  lessonId: Id;
  moduleId: Id;
  courseId: Id;
  title: string;
  transcriptText: string | null;
  hasVideo: boolean;
  completed: boolean;
  completedAt: Timestamp | null;
}

export interface LessonCompleteResult {
  lessonProgress: LessonProgressResult;
  certificate: CertificateStatus | null;
}
