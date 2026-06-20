"""Evidence domain entities — frozen dataclasses, no SQLAlchemy."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

EVIDENCE_TYPES = (
    "corroboration", "contradiction", "context",
    "primary_source", "secondary_source", "inference",
)
RELATIONSHIPS = ("supports", "contradicts", "contextualizes")

# Enforced in code, not just in the prompt (§ Wave B spec).
TYPE_TO_RELATIONSHIP: dict[str, str] = {
    "contradiction": "contradicts",
    "corroboration": "supports",
    "primary_source": "supports",
    "secondary_source": "supports",
    "context": "contextualizes",
    "inference": "contextualizes",
}

# Cost control: the linker only ever sees this much of a candidate body.
EXCERPT_CHARS = 500


@dataclass(frozen=True)
class CandidateItem:
    """One corpus hit handed to the evidence linker."""

    intake_item_id: uuid.UUID
    subject: str | None
    body_text_excerpt: str
    received_at: datetime
    source_id: uuid.UUID


@dataclass(frozen=True)
class LinkResult:
    """One linker judgment, already validated/corrected by the parser."""

    intake_item_id: uuid.UUID
    evidence_type: str
    relationship: str
    strength: float
    include: bool


@dataclass(frozen=True)
class EvidenceRecord:
    id: uuid.UUID
    workspace_id: uuid.UUID
    intake_item_id: uuid.UUID
    evidence_type: str
    text: str
    source_deleted: bool
    created_at: datetime
