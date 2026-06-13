"""Conflict domain entities — frozen dataclasses, no SQLAlchemy."""
from __future__ import annotations

from dataclasses import dataclass

CONFLICT_TYPES = (
    "direct_contradiction",
    "factual_disagreement",
    "temporal_inconsistency",
    "scope_difference",
)
# The model defaults here on an unrecognized type (detector.py contract).
DEFAULT_CONFLICT_TYPE = "factual_disagreement"


@dataclass(frozen=True)
class ConflictResult:
    """One detector verdict on a claim pair. is_conflict=False → no record."""

    is_conflict: bool
    conflict_type: str
    severity: float
    reasoning: str
