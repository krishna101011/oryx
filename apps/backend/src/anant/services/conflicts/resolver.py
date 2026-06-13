"""Auto-resolve decision logic — pure, no I/O (ADR-033).

A detected conflict auto-resolves ONLY when ALL FIVE conditions hold. Any
single failure escalates the conflict to an analyst. The decision function is
pure so each condition can be unit-tested in isolation (one failing condition
must block resolution).
"""
from __future__ import annotations

from dataclasses import dataclass

AUTO_RESOLVE_SEVERITY_MAX = 0.3          # condition 1: severity < 0.3
AUTO_RESOLVE_SCORE_RATIO = 2.0           # condition 2: winner > 2x loser
AUTO_RESOLVE_TYPES = (                    # condition 3
    "factual_disagreement",
    "temporal_inconsistency",
)
SOURCE_ACCURACY_CEILING = 0.7            # condition 5: neither source > 0.7


@dataclass(frozen=True)
class AutoResolveDecision:
    auto_resolve: bool
    winner_is_a: bool | None
    score_ratio: float | None
    # Per-condition booleans, surfaced into the audit log for traceability.
    conditions: dict[str, bool]


def evaluate_auto_resolve(
    *,
    severity: float,
    conflict_type: str,
    score_a: float | None,
    score_b: float | None,
    a_requires_review: bool,
    b_requires_review: bool,
    a_source_accuracy: float,
    b_source_accuracy: float,
) -> AutoResolveDecision:
    """Decide whether a conflict auto-resolves and, if so, which claim wins.

    Condition 2 needs both claims scored; an unscored claim (None) makes the
    ratio incomputable, which blocks auto-resolve (the conservative default).
    A loser score of exactly 0 is treated as incomputable for the same reason.
    """
    cond_severity = severity < AUTO_RESOLVE_SEVERITY_MAX
    cond_type = conflict_type in AUTO_RESOLVE_TYPES
    cond_no_review = not a_requires_review and not b_requires_review
    cond_source_accuracy = (
        a_source_accuracy <= SOURCE_ACCURACY_CEILING
        and b_source_accuracy <= SOURCE_ACCURACY_CEILING
    )

    cond_score_ratio = False
    winner_is_a: bool | None = None
    score_ratio: float | None = None
    if score_a is not None and score_b is not None:
        higher = max(score_a, score_b)
        lower = min(score_a, score_b)
        if lower > 0.0 and higher > AUTO_RESOLVE_SCORE_RATIO * lower:
            cond_score_ratio = True
            score_ratio = higher / lower
            winner_is_a = score_a >= score_b

    conditions = {
        "severity": cond_severity,
        "score_ratio": cond_score_ratio,
        "conflict_type": cond_type,
        "no_analyst_review": cond_no_review,
        "source_accuracy": cond_source_accuracy,
    }
    auto_resolve = all(conditions.values())
    if not auto_resolve:
        # Winner is only meaningful when we actually resolve.
        winner_is_a = None
    return AutoResolveDecision(
        auto_resolve=auto_resolve,
        winner_is_a=winner_is_a,
        score_ratio=score_ratio,
        conditions=conditions,
    )
