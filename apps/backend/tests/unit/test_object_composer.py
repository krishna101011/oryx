"""ObjectComposer pure logic (Wave E): epistemic-type selection + the
weighted-minimum score with epistemic ceilings. No DB."""
from __future__ import annotations

import pytest

from oryx.services.intelligence.composer import compute_score, select_epistemic_type

# ---------------- epistemic type = weakest constituent ----------------


def test_type_empty_is_unclassified() -> None:
    assert select_epistemic_type([]) == "unclassified"


@pytest.mark.parametrize(
    "t", ["fact", "claim", "speculation", "rumor", "opinion"]
)
def test_type_single_passthrough(t: str) -> None:
    assert select_epistemic_type([t]) == t


def test_type_unclassified_maps_to_rumor() -> None:
    assert select_epistemic_type(["unclassified"]) == "rumor"


def test_type_fact_and_claim_picks_claim() -> None:
    assert select_epistemic_type(["fact", "claim"]) == "claim"


def test_type_fact_and_opinion_picks_opinion() -> None:
    assert select_epistemic_type(["fact", "opinion"]) == "opinion"


def test_type_claim_and_speculation_picks_speculation() -> None:
    assert select_epistemic_type(["claim", "speculation"]) == "speculation"


def test_type_rumor_and_opinion_picks_opinion() -> None:
    assert select_epistemic_type(["rumor", "opinion"]) == "opinion"


def test_type_speculation_and_rumor_picks_rumor() -> None:
    assert select_epistemic_type(["speculation", "rumor"]) == "rumor"


def test_type_unclassified_beats_fact() -> None:
    # unclassified counts as rumor — more uncertain than fact.
    assert select_epistemic_type(["unclassified", "fact"]) == "rumor"


def test_type_opinion_beats_unclassified() -> None:
    assert select_epistemic_type(["unclassified", "opinion"]) == "opinion"


def test_type_unknown_alone_is_unclassified() -> None:
    assert select_epistemic_type(["nonsense"]) == "unclassified"


# ---------------- weighted-minimum score + ceilings ----------------


def test_score_empty_is_none() -> None:
    assert compute_score([], "fact") is None


def test_score_single_value_uncapped() -> None:
    # min == mean == 0.8 → raw 0.8 ≤ fact ceiling 1.0.
    assert compute_score([0.8], "fact") == pytest.approx(0.8)


def test_score_weighted_minimum_formula() -> None:
    # min 0.4 * 0.60 + mean 0.6 * 0.40 = 0.24 + 0.24 = 0.48.
    assert compute_score([0.8, 0.4], "fact") == pytest.approx(0.48)


def test_score_three_values() -> None:
    # min 0.6, mean 0.8 → 0.36 + 0.32 = 0.68 (claim ceiling 0.85, uncapped).
    assert compute_score([0.6, 1.0, 0.8], "claim") == pytest.approx(0.68)


@pytest.mark.parametrize(
    "etype,ceiling",
    [
        ("fact", 1.00),
        ("claim", 0.85),
        ("speculation", 0.60),
        ("rumor", 0.40),
        ("opinion", 0.30),
        ("unclassified", 0.40),
    ],
)
def test_score_capped_at_ceiling(etype: str, ceiling: float) -> None:
    # A high raw (all 0.95) is capped at the epistemic ceiling.
    assert compute_score([0.95, 0.95], etype) == pytest.approx(min(0.95, ceiling))


def test_score_below_ceiling_not_capped() -> None:
    # claim ceiling 0.85; raw 0.2 stays 0.2.
    assert compute_score([0.2, 0.2], "claim") == pytest.approx(0.2)


def test_score_unclassified_uses_rumor_ceiling() -> None:
    assert compute_score([1.0, 1.0], "unclassified") == pytest.approx(0.40)


@pytest.mark.parametrize(
    "types,expected",
    [
        (["fact", "claim", "opinion"], "opinion"),
        (["fact", "claim"], "claim"),
        (["claim", "claim"], "claim"),
        (["speculation", "fact"], "speculation"),
        (["rumor", "fact", "claim"], "rumor"),
        (["opinion", "opinion"], "opinion"),
        (["unclassified", "unclassified"], "rumor"),
        (["unclassified", "speculation"], "rumor"),  # rumor (unclassified) weaker
        (["unclassified", "claim"], "rumor"),
        (["fact", "speculation", "opinion"], "opinion"),
        (["claim", "rumor"], "rumor"),
        (["speculation", "claim", "fact"], "speculation"),
        (["fact", "fact", "fact"], "fact"),
        (["speculation", "speculation"], "speculation"),
        (["rumor", "rumor", "rumor"], "rumor"),
        (["fact", "rumor"], "rumor"),
        (["claim", "opinion", "fact"], "opinion"),
    ],
)
def test_type_selection_table(types: list[str], expected: str) -> None:
    assert select_epistemic_type(types) == expected


@pytest.mark.parametrize(
    "scores,etype,expected",
    [
        ([0.9], "fact", 0.9),
        ([1.0], "claim", 0.85),
        ([0.5, 0.5], "fact", 0.5),
        ([0.2, 0.8], "claim", 0.32),
        ([0.6, 0.6, 0.6], "speculation", 0.6),
        ([0.7, 0.9], "rumor", 0.40),
        ([0.1, 0.1], "opinion", 0.1),
        ([0.3, 0.5, 0.7], "fact", 0.38),
        ([0.4], "speculation", 0.4),
        ([0.95, 0.05], "claim", 0.23),
        ([1.0, 1.0, 1.0], "opinion", 0.30),
        ([0.5], "unclassified", 0.40),
        ([0.0, 0.0], "fact", 0.0),
        ([1.0], "fact", 1.0),
        ([0.85, 0.85], "claim", 0.85),
        ([0.9, 0.3], "speculation", 0.42),
        ([0.25], "rumor", 0.25),
        ([0.2, 0.2], "opinion", 0.2),
    ],
)
def test_score_table(scores: list[float], etype: str, expected: float) -> None:
    assert compute_score(scores, etype) == pytest.approx(expected)
