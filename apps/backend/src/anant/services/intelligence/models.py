"""Intelligence domain entities — frozen dataclasses, no SQLAlchemy."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

# Composition epistemic hierarchy, most → least uncertain. The composed object
# takes the MOST uncertain (earliest) type among its active claims.
COMPOSITION_HIERARCHY = ("opinion", "rumor", "speculation", "claim", "fact")

# unclassified is treated as 'rumor' for composition (spec §STEP2.3).
UNCLASSIFIED_AS = "rumor"

# Epistemic ceilings for the COMPOSED score. Differs from the scorer only in
# that unclassified maps to rumor's 0.40 (composition never leaves a score
# unbounded).
COMPOSITION_CEILINGS: dict[str, float] = {
    "fact": 1.00,
    "claim": 0.85,
    "speculation": 0.60,
    "rumor": 0.40,
    "opinion": 0.30,
    "unclassified": 0.40,
}


@dataclass(frozen=True)
class IntelligenceObjectResult:
    epistemic_type: str
    confidence_score: float | None
    verification_status: str
    claim_ids: list[uuid.UUID]
    conflict_ids: list[uuid.UUID]
    key_facts: dict[str, Any]
    headline: str
    scoring_version: int
