"""Request models for the calendar router.

Request bodies are snake_case (research/intake convention); responses are built
as camelCase dicts in the router to mirror the shared-types contract.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ScheduleDraftRequest(BaseModel):
    draft_id: str
    target_id: str
    scheduled_at: datetime
