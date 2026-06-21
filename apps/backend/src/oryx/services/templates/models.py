"""Templates domain entity — frozen, no SQLAlchemy."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentTemplate:
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    format: str
    tone: str
    max_words: int | None
    min_words: int | None
    structure_hint: str | None
    is_default: bool
