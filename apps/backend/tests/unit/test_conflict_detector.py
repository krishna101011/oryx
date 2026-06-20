"""ConflictDetectorAI parsing + safety posture (Wave D). No network."""
from __future__ import annotations

import pytest

from oryx.services.claims.extractor import AnthropicResult
from oryx.services.conflicts.detector import (
    NO_CONFLICT,
    ConflictDetectorAI,
    _parse,
)


def test_parse_valid_conflict() -> None:
    out = _parse(
        '{"is_conflict": true, "conflict_type": "direct_contradiction", '
        '"severity": 0.85, "reasoning": "they exclude each other"}'
    )
    assert out is not None
    assert out.is_conflict is True
    assert out.conflict_type == "direct_contradiction"
    assert out.severity == 0.85
    assert out.reasoning == "they exclude each other"


def test_parse_is_conflict_false_returns_no_conflict() -> None:
    out = _parse('{"is_conflict": false, "conflict_type": "scope_difference"}')
    assert out is NO_CONFLICT
    assert out.is_conflict is False


def test_parse_unparseable_returns_none() -> None:
    assert _parse("not json at all") is None
    assert _parse("[1, 2, 3]") is None  # not an object


def test_parse_invalid_conflict_type_defaults() -> None:
    out = _parse('{"is_conflict": true, "conflict_type": "nonsense", "severity": 0.5}')
    assert out is not None
    assert out.conflict_type == "factual_disagreement"  # DEFAULT


def test_parse_severity_clamped_and_defaulted() -> None:
    high = _parse('{"is_conflict": true, "conflict_type": "factual_disagreement", "severity": 9}')
    assert high is not None and high.severity == 1.0
    low = _parse('{"is_conflict": true, "conflict_type": "factual_disagreement", "severity": -3}')
    assert low is not None and low.severity == 0.0
    missing = _parse('{"is_conflict": true, "conflict_type": "factual_disagreement"}')
    assert missing is not None and missing.severity == 0.5
    boolish = _parse(
        '{"is_conflict": true, "conflict_type": "factual_disagreement", "severity": true}'
    )
    assert boolish is not None and boolish.severity == 0.5


def test_parse_strips_code_fence() -> None:
    out = _parse(
        '```json\n{"is_conflict": true, "conflict_type": "scope_difference", '
        '"severity": 0.4}\n```'
    )
    assert out is not None and out.conflict_type == "scope_difference"


def test_parse_missing_reasoning_is_empty() -> None:
    out = _parse('{"is_conflict": true, "conflict_type": "scope_difference", "severity": 0.4}')
    assert out is not None and out.reasoning == ""


def test_parse_reasoning_truncated() -> None:
    long_reason = "x" * 500
    out = _parse(
        '{"is_conflict": true, "conflict_type": "scope_difference", '
        f'"severity": 0.4, "reasoning": "{long_reason}"}}'
    )
    assert out is not None and len(out.reasoning) == 280


def test_parse_non_dict_entry_is_none() -> None:
    assert _parse('"just a string"') is None
    assert _parse("42") is None


def test_parse_severity_string_defaulted() -> None:
    out = _parse(
        '{"is_conflict": true, "conflict_type": "scope_difference", "severity": "high"}'
    )
    assert out is not None and out.severity == 0.5


def test_parse_missing_is_conflict_defaults_false() -> None:
    out = _parse('{"conflict_type": "scope_difference", "severity": 0.4}')
    assert out is NO_CONFLICT


@pytest.mark.asyncio
async def test_detect_happy_path(monkeypatch) -> None:
    async def fake_call(**kwargs):
        return AnthropicResult(
            text='{"is_conflict": true, "conflict_type": "temporal_inconsistency", '
            '"severity": 0.6, "reasoning": "dates clash"}',
            input_tokens=10,
            output_tokens=5,
        )

    monkeypatch.setattr(
        "oryx.services.conflicts.detector.call_anthropic", fake_call
    )
    result = await ConflictDetectorAI().detect(
        subject="Acme", a_predicate="rose", a_object="10%",
        b_predicate="fell", b_object="10%",
    )
    assert result.result.is_conflict is True
    assert result.result.conflict_type == "temporal_inconsistency"
    assert result.tokens_used == 15


@pytest.mark.asyncio
async def test_detect_parse_failure_is_no_conflict(monkeypatch) -> None:
    async def fake_call(**kwargs):
        return AnthropicResult(text="garbage", input_tokens=3, output_tokens=2)

    monkeypatch.setattr(
        "oryx.services.conflicts.detector.call_anthropic", fake_call
    )
    result = await ConflictDetectorAI().detect(
        subject="Acme", a_predicate="rose", a_object=None,
        b_predicate="fell", b_object=None,
    )
    assert result.result.is_conflict is False  # safe default
    assert result.tokens_used == 5
