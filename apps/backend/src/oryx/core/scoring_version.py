"""Current confidence-scoring formula version (ADR-032).

Bumping this is a code deployment, never a DB write. An intelligence object
whose `scoring_version` is below this value is stale; the UI surfaces a
recalculate CTA and an analyst re-scores manually (never auto-recompute).
"""
from __future__ import annotations

CURRENT_SCORING_VERSION = 1
