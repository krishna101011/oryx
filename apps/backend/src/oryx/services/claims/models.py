"""Claims domain entities — frozen dataclasses, no SQLAlchemy.

The repository converts between ORM rows (core/models.py) and these.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

EPISTEMIC_TYPES = (
    "fact", "claim", "rumor", "speculation", "opinion", "unclassified",
)


@dataclass(frozen=True)
class ClaimTriple:
    """One atomic assertion as the extractor returns it."""

    subject: str
    predicate: str
    object: str | None
    text: str


@dataclass(frozen=True)
class ClaimEntity:
    id: uuid.UUID
    workspace_id: uuid.UUID
    intake_item_id: uuid.UUID
    text: str
    subject: str
    predicate: str
    object: str | None
    epistemic_type: str
    extractor_version: int
    classifier_version: int | None
    requires_analyst_review: bool
    superseded_by: uuid.UUID | None
    created_at: datetime
