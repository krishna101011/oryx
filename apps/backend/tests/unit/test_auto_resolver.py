"""Auto-resolve decision logic (Wave D, ADR-033).

The mandatory invariant: a conflict auto-resolves ONLY when ALL FIVE conditions
hold. Each test below flips exactly one condition to failing and asserts that
resolution is blocked; the baseline asserts all-five-pass resolves.
"""
from __future__ import annotations

from oryx.services.conflicts.resolver import evaluate_auto_resolve

# A fixture that satisfies all five conditions; tests perturb one field each.
BASELINE = dict(
    severity=0.1,                    # < 0.3
    conflict_type="factual_disagreement",  # in allowed set
    score_a=0.8,
    score_b=0.2,                     # 0.8 > 2 * 0.2
    a_requires_review=False,
    b_requires_review=False,
    a_source_accuracy=0.5,
    b_source_accuracy=0.5,           # neither > 0.7
)


def test_baseline_all_five_pass_resolves() -> None:
    d = evaluate_auto_resolve(**BASELINE)
    assert d.auto_resolve is True
    assert d.winner_is_a is True  # 0.8 >= 0.2
    assert d.score_ratio == 4.0
    assert all(d.conditions.values())


def test_condition1_severity_too_high_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "severity": 0.3})
    assert d.auto_resolve is False
    assert d.conditions["severity"] is False


def test_condition2_score_ratio_too_low_blocks() -> None:
    # 0.5 vs 0.3 → ratio 1.67 < 2.
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": 0.5, "score_b": 0.3})
    assert d.auto_resolve is False
    assert d.conditions["score_ratio"] is False


def test_condition2_unscored_claim_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "score_b": None})
    assert d.auto_resolve is False
    assert d.conditions["score_ratio"] is False


def test_condition2_zero_loser_score_blocks() -> None:
    # A literal-0 loser makes the ratio incomputable → conservative block.
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": 0.8, "score_b": 0.0})
    assert d.auto_resolve is False
    assert d.conditions["score_ratio"] is False


def test_condition3_wrong_conflict_type_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "conflict_type": "direct_contradiction"})
    assert d.auto_resolve is False
    assert d.conditions["conflict_type"] is False
    # scope_difference is also outside the auto-resolve set.
    d2 = evaluate_auto_resolve(**{**BASELINE, "conflict_type": "scope_difference"})
    assert d2.auto_resolve is False


def test_condition3_temporal_inconsistency_allowed() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "conflict_type": "temporal_inconsistency"})
    assert d.auto_resolve is True


def test_condition4_requires_review_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "a_requires_review": True})
    assert d.auto_resolve is False
    assert d.conditions["no_analyst_review"] is False
    d2 = evaluate_auto_resolve(**{**BASELINE, "b_requires_review": True})
    assert d2.auto_resolve is False


def test_condition5_high_source_accuracy_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "a_source_accuracy": 0.71})
    assert d.auto_resolve is False
    assert d.conditions["source_accuracy"] is False
    d2 = evaluate_auto_resolve(**{**BASELINE, "b_source_accuracy": 0.9})
    assert d2.auto_resolve is False


def test_condition5_exactly_ceiling_allowed() -> None:
    # 0.7 is NOT > 0.7 — the boundary is inclusive of the allowed side.
    d = evaluate_auto_resolve(
        **{**BASELINE, "a_source_accuracy": 0.7, "b_source_accuracy": 0.7}
    )
    assert d.auto_resolve is True


def test_winner_is_b_when_b_scores_higher() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": 0.2, "score_b": 0.8})
    assert d.auto_resolve is True
    assert d.winner_is_a is False


def test_blocked_decision_clears_winner() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "severity": 0.9})
    assert d.auto_resolve is False
    assert d.winner_is_a is None


def test_both_scores_none_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": None, "score_b": None})
    assert d.auto_resolve is False
    assert d.conditions["score_ratio"] is False


def test_score_a_none_blocks() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": None})
    assert d.auto_resolve is False


def test_severity_just_below_threshold_passes() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "severity": 0.299})
    assert d.conditions["severity"] is True
    assert d.auto_resolve is True


def test_ratio_exactly_2x_blocks() -> None:
    # higher == 2 * lower is NOT strictly greater → blocked.
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": 0.4, "score_b": 0.2})
    assert d.conditions["score_ratio"] is False
    assert d.auto_resolve is False


def test_equal_scores_block() -> None:
    d = evaluate_auto_resolve(**{**BASELINE, "score_a": 0.5, "score_b": 0.5})
    assert d.auto_resolve is False
