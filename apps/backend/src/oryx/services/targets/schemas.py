"""Request models for the targets + publishing routers.

Request bodies are snake_case (the research/intake convention); responses are
built as camelCase dicts in the router to mirror the shared-types contract.

There is deliberately NO response model carrying credentials — the router's
serializers omit the credentials/credentials_iv columns entirely (§13.2).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PublishChannelLiteral = Literal[
    "twitter_x",
    "linkedin",
    "email_newsletter",
    "notion",
    "webhook",
    "export",
]


class CreateTargetRequest(BaseModel):
    name: str
    channel: PublishChannelLiteral
    # Channel credential fields (api_key, secret, access_token, ...). Write-only:
    # validated, encrypted, and never echoed back.
    credentials: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class PublishRequest(BaseModel):
    target_ids: list[str]
