"""Request models for the templates router."""
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

ContentTone = Literal[
    "formal",
    "analytical",
    "conversational",
    "authoritative",
    "concise",
]


class CreateTemplateRequest(BaseModel):
    name: str
    format: ContentFormat
    tone: ContentTone = "analytical"
    max_words: int | None = None
    min_words: int | None = None
    structure_hint: str | None = None


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    tone: ContentTone | None = None
    max_words: int | None = None
    min_words: int | None = None
    structure_hint: str | None = None
    # If client sends is_default, service rejects with 400.
    is_default: bool | None = None
