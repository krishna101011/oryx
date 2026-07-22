"""EpistemicClassifierAI — single-word contract + conservative fallback."""
from __future__ import annotations

import pytest

from oryx.services.claims import classifier as classifier_module
from oryx.services.claims.classifier import (
    ALLOWED_TYPES,
    CLASSIFIER_VERSION,
    CONTEXT_CHARS,
    EpistemicClassifierAI,
)
from oryx.services.claims.extractor import AIProviderResult


def _fake_call(label: str, capture: dict | None = None):
    async def fake(**kwargs):
        if capture is not None:
            capture.update(kwargs)
        return AIProviderResult(text=label, input_tokens=30, output_tokens=2)

    return fake


def test_classifier_version_is_one() -> None:
    assert CLASSIFIER_VERSION == 1
    assert EpistemicClassifierAI.version == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("label", sorted(ALLOWED_TYPES))
async def test_allowed_labels_pass_through(
    label: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(classifier_module, "call_ai_provider", _fake_call(label))
    result = await EpistemicClassifierAI().classify("Some claim.", "context")
    assert result.epistemic_type == label
    assert result.requires_analyst_review is False
    assert result.tokens_used == 32


@pytest.mark.asyncio
async def test_label_is_normalized_before_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(classifier_module, "call_ai_provider", _fake_call("  Rumor\n"))
    result = await EpistemicClassifierAI().classify("Some claim.", "context")
    assert result.epistemic_type == "rumor"
    assert result.requires_analyst_review is False


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["maybe", "fact.", "unclassified", "claim rumor", ""])
async def test_contract_violation_defaults_to_claim_with_review(
    bad: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(classifier_module, "call_ai_provider", _fake_call(bad))
    result = await EpistemicClassifierAI().classify("Some claim.", "context")
    assert result.epistemic_type == "claim"
    assert result.requires_analyst_review is True


@pytest.mark.asyncio
async def test_context_is_truncated_to_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        classifier_module, "call_ai_provider", _fake_call("fact", captured)
    )
    long_context = "z" * (CONTEXT_CHARS * 3)
    await EpistemicClassifierAI().classify("Some claim.", long_context)
    # The user content embeds at most CONTEXT_CHARS of context.
    assert captured["user_content"].count("z") == CONTEXT_CHARS
