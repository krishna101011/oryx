"""Phase 8 Wave A — schema-shape checks, no DB required.

Course/Module/Lesson are platform-wide
(docs/PHASE_8_TRAINING_ARCHITECTURE.md §2/§4) — this asserts that
structurally, not just by convention: no workspace_id column exists
anywhere in the training schema, so there is no "which workspace" question
a query could even ask.
"""
from __future__ import annotations

from oryx.core.models import (
    Certificate,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)


def test_course_has_no_workspace_id_column() -> None:
    assert "workspace_id" not in Course.__table__.columns.keys()


def test_module_and_lesson_also_carry_no_workspace_id() -> None:
    """Platform-wide-ness isn't just Course's property — nothing downstream
    of it should reintroduce a workspace scope either."""
    assert "workspace_id" not in Module.__table__.columns.keys()
    assert "workspace_id" not in Lesson.__table__.columns.keys()


def test_enrollment_primary_key_is_account_and_course() -> None:
    pk_cols = {c.name for c in Enrollment.__table__.primary_key.columns}
    assert pk_cols == {"account_id", "course_id"}


def test_lesson_progress_primary_key_is_account_and_lesson() -> None:
    pk_cols = {c.name for c in LessonProgress.__table__.primary_key.columns}
    assert pk_cols == {"account_id", "lesson_id"}


def test_certificate_primary_key_is_account_and_course() -> None:
    pk_cols = {c.name for c in Certificate.__table__.primary_key.columns}
    assert pk_cols == {"account_id", "course_id"}
