"""ClaimExtractorAI — JSON contract parsing, caps, and failure flagging.

DB-free; the Anthropic HTTP call is monkeypatched at the module seam.
"""
from __future__ import annotations

import json

import pytest

from oryx.services.claims import extractor as extractor_module
from oryx.services.claims.extractor import (
    EXTRACTOR_VERSION,
    MAX_CLAIMS_PER_ITEM,
    AnthropicResult,
    ClaimExtractorAI,
    _parse_triples,
)

VALID_ENTRY = {
    "subject": "Apple Inc",
    "predicate": "reported revenue of",
    "object": "$94.9 billion",
    "text": "Apple Inc reported revenue of $94.9 billion in Q1 2024.",
}


def _fake_call(text: str, tokens: tuple[int, int] = (100, 50)):
    async def fake(**kwargs):
        return AnthropicResult(
            text=text, input_tokens=tokens[0], output_tokens=tokens[1]
        )

    return fake


def test_extractor_version_is_one() -> None:
    assert EXTRACTOR_VERSION == 1
    assert ClaimExtractorAI.version == 1


# ---------------------------------------------------------------------------
# _parse_triples — the model-output contract
# ---------------------------------------------------------------------------

def test_parses_valid_array() -> None:
    triples = _parse_triples(json.dumps([VALID_ENTRY]))
    assert triples is not None and len(triples) == 1
    t = triples[0]
    assert t.subject == "Apple Inc"
    assert t.predicate == "reported revenue of"
    assert t.object == "$94.9 billion"
    assert t.text.startswith("Apple Inc reported")


def test_null_object_is_valid() -> None:
    entry = {**VALID_ENTRY, "object": None}
    triples = _parse_triples(json.dumps([entry]))
    assert triples is not None
    assert triples[0].object is None


def test_empty_array_is_valid_zero_claims() -> None:
    assert _parse_triples("[]") == []


@pytest.mark.parametrize(
    "raw",
    [
        "Here are the claims: []",          # prose around JSON
        '{"subject": "x"}',                  # object, not array
        json.dumps([{**VALID_ENTRY, "subject": ""}]),   # blank subject
        json.dumps([{**VALID_ENTRY, "text": None}]),    # missing text
        json.dumps([{**VALID_ENTRY, "object": 42}]),    # non-string object
        json.dumps(["not-a-dict"]),
        "",
    ],
)
def test_malformed_output_returns_none(raw: str) -> None:
    assert _parse_triples(raw) is None


# ---------------------------------------------------------------------------
# extract()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_returns_triples_and_token_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor_module, "call_anthropic", _fake_call(json.dumps([VALID_ENTRY]))
    )
    result = await ClaimExtractorAI().extract("Some body text")
    assert not result.parse_failed
    assert len(result.triples) == 1
    assert result.tokens_used == 150  # input + output


@pytest.mark.asyncio
async def test_extract_caps_at_max_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    many = [
        {**VALID_ENTRY, "text": f"{VALID_ENTRY['text']} variant {i}"}
        for i in range(MAX_CLAIMS_PER_ITEM + 5)
    ]
    monkeypatch.setattr(extractor_module, "call_anthropic", _fake_call(json.dumps(many)))
    result = await ClaimExtractorAI().extract("body")
    assert len(result.triples) == MAX_CLAIMS_PER_ITEM


@pytest.mark.asyncio
async def test_extract_flags_unparseable_output_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extractor_module, "call_anthropic", _fake_call("I think the claims are...")
    )
    result = await ClaimExtractorAI().extract("body")
    assert result.parse_failed
    assert result.triples == []
    assert result.tokens_used == 150  # spend is still real and still counted


@pytest.mark.asyncio
async def test_fenced_json_output_is_salvaged(monkeypatch: pytest.MonkeyPatch) -> None:
    fenced = f"```json\n{json.dumps([VALID_ENTRY])}\n```"
    monkeypatch.setattr(extractor_module, "call_anthropic", _fake_call(fenced))
    result = await ClaimExtractorAI().extract("body")
    assert not result.parse_failed
    assert len(result.triples) == 1


@pytest.mark.asyncio
async def test_oversized_input_is_truncated_before_the_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from oryx.services.claims.extractor import EXTRACTOR_INPUT_MAX_CHARS

    captured: dict = {}

    async def fake(**kwargs):
        captured.update(kwargs)
        return AnthropicResult(text="[]", input_tokens=10, output_tokens=1)

    monkeypatch.setattr(extractor_module, "call_anthropic", fake)
    await ClaimExtractorAI().extract("z" * (EXTRACTOR_INPUT_MAX_CHARS * 2))
    assert len(captured["user_content"]) == EXTRACTOR_INPUT_MAX_CHARS
