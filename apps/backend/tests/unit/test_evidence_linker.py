"""EvidenceLinkerAI — batch contract, mapping enforcement, hallucination guard."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest

from anant.services.claims.extractor import AnthropicResult
from anant.services.evidence import linker as linker_module
from anant.services.evidence.linker import LINKER_VERSION, EvidenceLinkerAI
from anant.services.evidence.models import CandidateItem


def _candidate(item_id: uuid.UUID | None = None) -> CandidateItem:
    return CandidateItem(
        intake_item_id=item_id or uuid.uuid4(),
        subject="Apple results",
        body_text_excerpt="Apple Inc reported revenue of $94.9 billion.",
        received_at=datetime.now(UTC),
        source_id=uuid.uuid4(),
    )


def _entry(item_id: uuid.UUID, **overrides) -> dict:
    entry = {
        "intake_item_id": str(item_id),
        "evidence_type": "corroboration",
        "relationship": "supports",
        "strength": 0.7,
        "include": True,
    }
    entry.update(overrides)
    return entry


def _fake_call(text: str, capture: dict | None = None):
    async def fake(**kwargs):
        if capture is not None:
            capture.update(kwargs)
        return AnthropicResult(text=text, input_tokens=200, output_tokens=40)

    return fake


def test_linker_version_is_one() -> None:
    assert LINKER_VERSION == 1
    assert EvidenceLinkerAI.version == 1


@pytest.mark.asyncio
async def test_single_batched_call_contains_every_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = [_candidate() for _ in range(4)]
    captured: dict = {}
    calls = {"n": 0}

    async def fake(**kwargs):
        calls["n"] += 1
        captured.update(kwargs)
        return AnthropicResult(text="[]", input_tokens=10, output_tokens=1)

    monkeypatch.setattr(linker_module, "call_anthropic", fake)
    await EvidenceLinkerAI().link("Some claim.", candidates)
    assert calls["n"] == 1  # one call per claim, never per candidate
    for c in candidates:
        assert str(c.intake_item_id) in captured["user_content"]


@pytest.mark.asyncio
async def test_valid_results_pass_through(monkeypatch: pytest.MonkeyPatch) -> None:
    c = _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps([_entry(c.intake_item_id)])),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert not result.parse_failed
    assert result.tokens_used == 240
    [r] = result.results
    assert r.intake_item_id == c.intake_item_id
    assert r.evidence_type == "corroboration"
    assert r.relationship == "supports"
    assert r.strength == 0.7
    assert r.include is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("etype", "wrong_rel", "expected_rel"),
    [
        ("contradiction", "supports", "contradicts"),
        ("corroboration", "contradicts", "supports"),
        ("primary_source", "contextualizes", "supports"),
        ("secondary_source", "contradicts", "supports"),
        ("context", "supports", "contextualizes"),
        ("inference", "contradicts", "contextualizes"),
    ],
)
async def test_type_to_relationship_mapping_enforced_in_code(
    etype: str, wrong_rel: str, expected_rel: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps(
            [_entry(c.intake_item_id, evidence_type=etype, relationship=wrong_rel)]
        )),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert result.results[0].relationship == expected_rel  # corrected silently


@pytest.mark.asyncio
async def test_invalid_evidence_type_skips_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good, bad = _candidate(), _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps([
            _entry(bad.intake_item_id, evidence_type="hearsay"),
            _entry(good.intake_item_id),
        ])),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [good, bad])
    assert [r.intake_item_id for r in result.results] == [good.intake_item_id]


@pytest.mark.asyncio
async def test_hallucinated_id_is_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    c = _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps([
            _entry(uuid.uuid4()),          # id not in the candidate set
            _entry(c.intake_item_id),
        ])),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert [r.intake_item_id for r in result.results] == [c.intake_item_id]


@pytest.mark.asyncio
@pytest.mark.parametrize(("raw", "clamped"), [(1.7, 1.0), (-0.2, 0.0), (0.42, 0.42)])
async def test_strength_is_clamped(
    raw: float, clamped: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    c = _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps([_entry(c.intake_item_id, strength=raw)])),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert result.results[0].strength == clamped


@pytest.mark.asyncio
async def test_include_false_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    c = _candidate()
    monkeypatch.setattr(
        linker_module, "call_anthropic",
        _fake_call(json.dumps([_entry(c.intake_item_id, include=False)])),
    )
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert result.results[0].include is False


@pytest.mark.asyncio
async def test_prose_output_flags_parse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        linker_module, "call_anthropic", _fake_call("These look relevant to me.")
    )
    result = await EvidenceLinkerAI().link("Some claim.", [_candidate()])
    assert result.parse_failed
    assert result.results == []
    assert result.tokens_used == 240  # spend still counted


@pytest.mark.asyncio
async def test_fenced_json_is_salvaged(monkeypatch: pytest.MonkeyPatch) -> None:
    c = _candidate()
    fenced = f"```json\n{json.dumps([_entry(c.intake_item_id)])}\n```"
    monkeypatch.setattr(linker_module, "call_anthropic", _fake_call(fenced))
    result = await EvidenceLinkerAI().link("Some claim.", [c])
    assert not result.parse_failed
    assert len(result.results) == 1
