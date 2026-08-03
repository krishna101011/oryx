"""Training/Academy router — Phase 8 Wave A (authoring) + Wave B (learner-
facing enroll/progress/certificate).

Course/Module/Lesson are platform-wide, not workspace-scoped
(docs/PHASE_8_TRAINING_ARCHITECTURE.md §2) — authoring endpoints are gated
by Account.is_platform_admin (require_platform_admin), NOT
require_capability: no ActiveWorkspaceContext/get_active_workspace appears
anywhere in this file, by design (§4's corrected reasoning — a
workspace-role capability check cannot coherently apply to a resource that
belongs to no workspace).

Wave B's learner-facing endpoints (enroll/complete/progress) use the SAME
reasoning one level down: any real signed-in account should be able to
enroll in and track its own progress through the platform-wide catalog —
there is no workspace role to check here either, so these are gated by
plain get_current_account, never is_platform_admin or any capability.
Enrollment is deliberately NOT a precondition for completing a lesson
(CertificateRepository's own issuance rule already never references
Enrollment — see repository.py) — not an oversight, matching that existing
independence rather than inventing a new gate.

Response bodies are plain dicts, not oryx.shared.types models: no frontend
consumes these yet (explicitly out of scope this wave), and gen-pydantic.ts's
unused-export check would flag a TS mirror with zero real references — see
services/training/models.py's docstring.

The /training/ping stub route is kept — test_health.py exercises every
service's ping.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.dependencies import (
    db_session,
    envelope,
    get_current_account,
    get_request_id,
    require_platform_admin,
)
from oryx.core.errors import NotFoundError, VideoProviderUnavailableError
from oryx.core.models import Account, Course, Lesson, Module
from oryx.core.video_provider import VideoProviderError, get_video_provider
from oryx.services.training.models import (
    CourseCreateRequest,
    CourseUpdateRequest,
    LessonCreateRequest,
    LessonUpdateRequest,
    ModuleCreateRequest,
    ModuleUpdateRequest,
)
from oryx.services.training.repository import (
    CertificateRepository,
    CourseRepository,
    EnrollmentRepository,
    LessonProgressRepository,
    LessonRepository,
    ModuleRepository,
)

router = APIRouter(tags=["training"])


@router.get("/training/ping")
async def ping(request: Request) -> dict:
    return envelope(
        {"service": "training", "pong": True}, request_id=get_request_id(request)
    )


def _iso(value: datetime) -> str:
    return value.isoformat()


def _course_dict(row: Course) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "createdBy": str(row.created_by),
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def _module_dict(row: Module) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "courseId": str(row.course_id),
        "title": row.title,
        "order": row.order,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def _lesson_dict(row: Lesson) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "moduleId": str(row.module_id),
        "title": row.title,
        "videoAssetId": row.video_asset_id,
        "transcriptText": row.transcript_text,
        "order": row.order,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


# --------------------------------------------------------------------------- #
# Courses
# --------------------------------------------------------------------------- #


@router.post("/training/courses")
async def create_course(
    body: CourseCreateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await CourseRepository(db).create(
        title=body.title, description=body.description, created_by=admin.id
    )
    return envelope(_course_dict(row), request_id=get_request_id(request))


@router.get("/training/courses")
async def list_courses(
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    rows = await CourseRepository(db).list_all()
    return envelope([_course_dict(r) for r in rows], request_id=get_request_id(request))


@router.get("/training/courses/{course_id}")
async def get_course(
    course_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    row = await CourseRepository(db).get(course_id)
    if row is None:
        raise NotFoundError("Course not found")
    return envelope(_course_dict(row), request_id=get_request_id(request))


@router.patch("/training/courses/{course_id}")
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = CourseRepository(db)
    row = await repo.get(course_id)
    if row is None:
        raise NotFoundError("Course not found")
    row = await repo.update(row, body.model_dump(exclude_unset=True))
    return envelope(_course_dict(row), request_id=get_request_id(request))


@router.delete("/training/courses/{course_id}")
async def delete_course(
    course_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = CourseRepository(db)
    row = await repo.get(course_id)
    if row is None:
        raise NotFoundError("Course not found")
    await repo.delete(row)
    return envelope({"deleted": True}, request_id=get_request_id(request))


# --------------------------------------------------------------------------- #
# Modules
# --------------------------------------------------------------------------- #


@router.post("/training/courses/{course_id}/modules")
async def create_module(
    course_id: uuid.UUID,
    body: ModuleCreateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    course = await CourseRepository(db).get(course_id)
    if course is None:
        raise NotFoundError("Course not found")
    row = await ModuleRepository(db).create(
        course_id=course_id, title=body.title, order=body.order
    )
    return envelope(_module_dict(row), request_id=get_request_id(request))


@router.get("/training/courses/{course_id}/modules")
async def list_modules(
    course_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    course = await CourseRepository(db).get(course_id)
    if course is None:
        raise NotFoundError("Course not found")
    rows = await ModuleRepository(db).list_for_course(course_id)
    return envelope([_module_dict(r) for r in rows], request_id=get_request_id(request))


@router.patch("/training/modules/{module_id}")
async def update_module(
    module_id: uuid.UUID,
    body: ModuleUpdateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = ModuleRepository(db)
    row = await repo.get(module_id)
    if row is None:
        raise NotFoundError("Module not found")
    row = await repo.update(row, body.model_dump(exclude_unset=True))
    return envelope(_module_dict(row), request_id=get_request_id(request))


@router.delete("/training/modules/{module_id}")
async def delete_module(
    module_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = ModuleRepository(db)
    row = await repo.get(module_id)
    if row is None:
        raise NotFoundError("Module not found")
    await repo.delete(row)
    return envelope({"deleted": True}, request_id=get_request_id(request))


# --------------------------------------------------------------------------- #
# Lessons
# --------------------------------------------------------------------------- #


@router.post("/training/modules/{module_id}/lessons")
async def create_lesson(
    module_id: uuid.UUID,
    body: LessonCreateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    module = await ModuleRepository(db).get(module_id)
    if module is None:
        raise NotFoundError("Module not found")
    row = await LessonRepository(db).create(
        module_id=module_id,
        title=body.title,
        video_asset_id=body.video_asset_id,
        transcript_text=body.transcript_text,
        order=body.order,
    )
    return envelope(_lesson_dict(row), request_id=get_request_id(request))


@router.get("/training/modules/{module_id}/lessons")
async def list_lessons(
    module_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    module = await ModuleRepository(db).get(module_id)
    if module is None:
        raise NotFoundError("Module not found")
    rows = await LessonRepository(db).list_for_module(module_id)
    return envelope([_lesson_dict(r) for r in rows], request_id=get_request_id(request))


@router.patch("/training/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: uuid.UUID,
    body: LessonUpdateRequest,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = LessonRepository(db)
    row = await repo.get(lesson_id)
    if row is None:
        raise NotFoundError("Lesson not found")
    row = await repo.update(row, body.model_dump(exclude_unset=True))
    return envelope(_lesson_dict(row), request_id=get_request_id(request))


@router.delete("/training/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = LessonRepository(db)
    row = await repo.get(lesson_id)
    if row is None:
        raise NotFoundError("Lesson not found")
    await repo.delete(row)
    return envelope({"deleted": True}, request_id=get_request_id(request))


# --------------------------------------------------------------------------- #
# Video (VideoProvider wiring, §3) — this can never succeed without real
# Cloudflare credentials, exactly like POST /billing/subscribe can never
# succeed without real Stripe/Razorpay credentials. It exists to prove the
# provider abstraction is really wired end-to-end, not just unit-tested in
# isolation — it does not attempt any live upload or playback.
# --------------------------------------------------------------------------- #


@router.post("/training/lessons/{lesson_id}/video-upload-url")
async def create_video_upload_url(
    lesson_id: uuid.UUID,
    request: Request,
    admin: Account = Depends(require_platform_admin),
    db: AsyncSession = Depends(db_session),
) -> dict:
    lesson = await LessonRepository(db).get(lesson_id)
    if lesson is None:
        raise NotFoundError("Lesson not found")
    provider = get_video_provider(get_settings())
    try:
        handle = await provider.create_upload_url(lesson_id=str(lesson_id))
    except VideoProviderError as exc:
        raise VideoProviderUnavailableError(
            details={
                "provider": exc.provider,
                "kind": exc.kind.value,
                "reason": exc.message,
            }
        ) from exc
    return envelope(
        {"assetId": handle.asset_id, "uploadUrl": handle.upload_url},
        request_id=get_request_id(request),
    )


# --------------------------------------------------------------------------- #
# Learner-facing: enroll / complete / progress (Wave B). Gated by plain
# get_current_account — no workspace context, no platform-admin check.
# Course/Module/Lesson have no workspace_id (§2), so there is no workspace
# role to check here either, same reasoning as authoring's §4 correction
# one level down.
# --------------------------------------------------------------------------- #


def _enrollment_dict(row) -> dict[str, Any]:
    return {
        "accountId": str(row.account_id),
        "courseId": str(row.course_id),
        "enrolledAt": _iso(row.enrolled_at),
    }


def _lesson_progress_dict(row) -> dict[str, Any]:
    return {
        "accountId": str(row.account_id),
        "lessonId": str(row.lesson_id),
        "completedAt": _iso(row.completed_at),
    }


def _certificate_dict(row) -> dict[str, Any]:
    return {
        "accountId": str(row.account_id),
        "courseId": str(row.course_id),
        "issuedAt": _iso(row.issued_at),
    }


@router.post("/training/courses/{course_id}/enroll")
async def enroll_in_course(
    course_id: uuid.UUID,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    course = await CourseRepository(db).get(course_id)
    if course is None:
        raise NotFoundError("Course not found")
    row = await EnrollmentRepository(db).enroll(account_id=account.id, course_id=course_id)
    return envelope(_enrollment_dict(row), request_id=get_request_id(request))


@router.post("/training/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: uuid.UUID,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    lesson = await LessonRepository(db).get(lesson_id)
    if lesson is None:
        raise NotFoundError("Lesson not found")
    # Lesson.module_id is a NOT NULL FK — the row is guaranteed to exist.
    module = await ModuleRepository(db).get(lesson.module_id)

    progress = await LessonProgressRepository(db).mark_complete(
        account_id=account.id, lesson_id=lesson_id
    )
    # Same transaction, same request — issuance fires the moment the final
    # lesson completes, not as a separate manual step (Phase 1's requirement).
    certificate = await CertificateRepository(db).issue_if_eligible(
        account_id=account.id, course_id=module.course_id
    )
    return envelope(
        {
            "lessonProgress": _lesson_progress_dict(progress),
            "certificate": _certificate_dict(certificate) if certificate is not None else None,
        },
        request_id=get_request_id(request),
    )


@router.get("/training/courses/{course_id}/progress")
async def get_course_progress(
    course_id: uuid.UUID,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    course = await CourseRepository(db).get(course_id)
    if course is None:
        raise NotFoundError("Course not found")

    enrollment = await EnrollmentRepository(db).get(account_id=account.id, course_id=course_id)
    lessons = await LessonRepository(db).list_for_course(course_id)
    completed_map = await LessonProgressRepository(db).completed_map_for_course(
        account_id=account.id, course_id=course_id
    )
    certificate = await CertificateRepository(db).get(account_id=account.id, course_id=course_id)

    return envelope(
        {
            "courseId": str(course_id),
            "enrollment": _enrollment_dict(enrollment) if enrollment is not None else None,
            "lessons": [
                {
                    "lessonId": str(lesson.id),
                    "moduleId": str(lesson.module_id),
                    "title": lesson.title,
                    "completed": lesson.id in completed_map,
                    "completedAt": (
                        _iso(completed_map[lesson.id]) if lesson.id in completed_map else None
                    ),
                }
                for lesson in lessons
            ],
            "certificate": _certificate_dict(certificate) if certificate is not None else None,
        },
        request_id=get_request_id(request),
    )
