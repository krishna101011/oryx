"""Research domain entities — frozen dataclasses, no SQLAlchemy."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectReadinessInput:
    """The two fields packet readiness depends on, per intelligence object."""

    id: str
    headline: str
    verification_status: str


@dataclass(frozen=True)
class ReadinessResult:
    is_ready: bool
    blockers: list[str]


def evaluate_readiness(
    objects: list[ObjectReadinessInput], acknowledged_ids: set[str]
) -> ReadinessResult:
    """Pure readiness gate. A packet is blocked while any object is rejected,
    or is contested without an explicit acknowledgement."""
    blockers: list[str] = []
    for obj in objects:
        if obj.verification_status == "analyst_rejected":
            blockers.append(f"Object '{obj.headline}' has been rejected")
        elif obj.verification_status == "contested" and obj.id not in acknowledged_ids:
            blockers.append(f"Object '{obj.headline}' has unacknowledged conflict")
    return ReadinessResult(is_ready=not blockers, blockers=blockers)
