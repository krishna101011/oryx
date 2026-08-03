"""Request bodies for Course/Module/Lesson authoring (Phase 8 Wave A).

Deliberately local to this service, not mirrored via oryx.shared.types —
no frontend consumes these yet (this wave is backend-only, per its own
scope), and gen-pydantic.ts's unused-export check would flag a TS mirror
with zero real references. Add a shared-types mirror in the wave that
actually wires a frontend against these endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel


class CourseCreateRequest(BaseModel):
    title: str
    description: str | None = None


class CourseUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None


class ModuleCreateRequest(BaseModel):
    title: str
    order: int = 0


class ModuleUpdateRequest(BaseModel):
    title: str | None = None
    order: int | None = None


class LessonCreateRequest(BaseModel):
    title: str
    video_asset_id: str | None = None
    transcript_text: str | None = None
    order: int = 0


class LessonUpdateRequest(BaseModel):
    title: str | None = None
    video_asset_id: str | None = None
    transcript_text: str | None = None
    order: int | None = None
