"""courses/modules/lessons/enrollments/lesson_progress/certificates
persistence (Phase 8 Wave A).

Update methods take a dict of ALREADY-filtered fields (the caller passes
body.model_dump(exclude_unset=True) at the router layer) rather than
every-field-optional keyword arguments — one shared _apply_updates helper,
not three near-identical field-by-field branches.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    Certificate,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)


def _apply_updates(row: Any, fields: dict[str, Any]) -> None:
    for key, value in fields.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)


class CourseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, *, title: str, description: str | None, created_by: uuid.UUID
    ) -> Course:
        row = Course(
            id=uuid.uuid4(), title=title, description=description, created_by=created_by
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get(self, course_id: uuid.UUID) -> Course | None:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Course]:
        result = await self.db.execute(select(Course).order_by(Course.created_at))
        return list(result.scalars().all())

    async def update(self, course: Course, fields: dict[str, Any]) -> Course:
        _apply_updates(course, fields)
        await self.db.flush()
        return course

    async def delete(self, course: Course) -> None:
        await self.db.delete(course)
        await self.db.flush()


class ModuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, course_id: uuid.UUID, title: str, order: int) -> Module:
        row = Module(id=uuid.uuid4(), course_id=course_id, title=title, order=order)
        self.db.add(row)
        await self.db.flush()
        return row

    async def get(self, module_id: uuid.UUID) -> Module | None:
        result = await self.db.execute(select(Module).where(Module.id == module_id))
        return result.scalar_one_or_none()

    async def list_for_course(self, course_id: uuid.UUID) -> list[Module]:
        result = await self.db.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.order, Module.created_at)
        )
        return list(result.scalars().all())

    async def update(self, module: Module, fields: dict[str, Any]) -> Module:
        _apply_updates(module, fields)
        await self.db.flush()
        return module

    async def delete(self, module: Module) -> None:
        await self.db.delete(module)
        await self.db.flush()


class LessonRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        module_id: uuid.UUID,
        title: str,
        video_asset_id: str | None,
        transcript_text: str | None,
        order: int,
    ) -> Lesson:
        row = Lesson(
            id=uuid.uuid4(),
            module_id=module_id,
            title=title,
            video_asset_id=video_asset_id,
            transcript_text=transcript_text,
            order=order,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get(self, lesson_id: uuid.UUID) -> Lesson | None:
        result = await self.db.execute(select(Lesson).where(Lesson.id == lesson_id))
        return result.scalar_one_or_none()

    async def list_for_module(self, module_id: uuid.UUID) -> list[Lesson]:
        result = await self.db.execute(
            select(Lesson)
            .where(Lesson.module_id == module_id)
            .order_by(Lesson.order, Lesson.created_at)
        )
        return list(result.scalars().all())

    async def update(self, lesson: Lesson, fields: dict[str, Any]) -> Lesson:
        _apply_updates(lesson, fields)
        await self.db.flush()
        return lesson

    async def delete(self, lesson: Lesson) -> None:
        await self.db.delete(lesson)
        await self.db.flush()


class EnrollmentRepository:
    """No HTTP endpoints this wave (authoring only, per task scope) —
    exercised directly by tests that need a real enrollment precondition."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enroll(self, *, account_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment:
        row = Enrollment(account_id=account_id, course_id=course_id)
        self.db.add(row)
        await self.db.flush()
        return row


class LessonProgressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def mark_complete(
        self, *, account_id: uuid.UUID, lesson_id: uuid.UUID
    ) -> LessonProgress:
        row = LessonProgress(account_id=account_id, lesson_id=lesson_id)
        self.db.add(row)
        await self.db.flush()
        return row


class CertificateRepository:
    """issue_if_eligible is the real §2 rule: "issued when every lesson in
    a course has a completion row" — computed by comparing the course's
    real total lesson count against this account's real completed-lesson
    count, never inferred from Enrollment alone (an enrollment row proves
    intent to take the course, not completion)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, *, account_id: uuid.UUID, course_id: uuid.UUID) -> Certificate | None:
        result = await self.db.execute(
            select(Certificate).where(
                Certificate.account_id == account_id, Certificate.course_id == course_id
            )
        )
        return result.scalar_one_or_none()

    async def issue_if_eligible(
        self, *, account_id: uuid.UUID, course_id: uuid.UUID
    ) -> Certificate | None:
        existing = await self.get(account_id=account_id, course_id=course_id)
        if existing is not None:
            return existing

        total_lessons = (
            await self.db.execute(
                select(func.count(Lesson.id))
                .join(Module, Lesson.module_id == Module.id)
                .where(Module.course_id == course_id)
            )
        ).scalar_one()
        if not total_lessons:
            return None

        completed_lessons = (
            await self.db.execute(
                select(func.count(LessonProgress.lesson_id))
                .join(Lesson, LessonProgress.lesson_id == Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .where(
                    Module.course_id == course_id,
                    LessonProgress.account_id == account_id,
                )
            )
        ).scalar_one()
        if completed_lessons < total_lessons:
            return None

        row = Certificate(account_id=account_id, course_id=course_id)
        self.db.add(row)
        await self.db.flush()
        return row
