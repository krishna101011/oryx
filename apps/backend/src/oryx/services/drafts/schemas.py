"""Request models for the drafts router.

Request bodies are snake_case (the research/intake convention); responses are
built as camelCase dicts in the router to mirror the shared-types contract.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ContentFormat = Literal[
    "tweet_thread",
    "linkedin_post",
    "newsletter_section",
    "article",
    "report_summary",
    "custom",
]


class GenerateDraftRequest(BaseModel):
    packet_id: str
    format: ContentFormat
    template_id: str | None = None
    instructions: str | None = None


class RegenerateDraftRequest(BaseModel):
    instructions: str | None = None


class SaveVersionRequest(BaseModel):
    content: str
    content_html: str | None = None
    edit_note: str | None = None


class SwitchFormatRequest(BaseModel):
    format: ContentFormat
    template_id: str | None = None


# --- Wave C: review workflow ---
# `note` requirement for reject/request-changes is enforced in the service
# layer (HTTP 400), not the schema, so the guard is owned in one place.
class ApproveDraftRequest(BaseModel):
    note: str | None = None


class RejectDraftRequest(BaseModel):
    note: str


class RequestChangesRequest(BaseModel):
    note: str
