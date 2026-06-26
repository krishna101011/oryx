"""Calendar domain dataclasses (frozen, no SQLAlchemy).

The ORM row (core.models.CalendarEntry) is serialized directly by the router,
mirroring the targets/publishing convention; the only domain object Wave E needs
is the scheduler's per-tick stat summary.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalendarTickStats:
    """One scheduler tick's outcome across both passes."""

    fired: int          # Pass A: calendar entries acted on (published/failed/left)
    redriven: int       # Pass B: pending publications re-invoked

    @property
    def acted(self) -> int:
        return self.fired + self.redriven
