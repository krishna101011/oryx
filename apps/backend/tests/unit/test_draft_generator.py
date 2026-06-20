"""DraftGeneratorAI — prompt structure + model selection (Wave A invariants #1, #5).

No DB / no network: these exercise the pure prompt-building surface and the
model constant. The source-only constraint and Sonnet selection are contractual,
so they get dedicated assertions.
"""
from __future__ import annotations

import uuid

from oryx.services.drafts.generator import (
    ANTHROPIC_MODEL_SONNET,
    SOURCE_ONLY_MARKER,
    DraftGeneratorAI,
    build_generation_prompt,
    build_system_context,
)
from oryx.services.drafts.models import ObjectSnapshot


def _obj(headline: str = "Acme raised $5B") -> ObjectSnapshot:
    return ObjectSnapshot(
        id=uuid.uuid4(),
        headline=headline,
        epistemic_type="fact",
        confidence_score=0.9,
        key_facts={"Acme": {"predicate": "raised", "object": "$5B"}},
    )


def test_generator_uses_sonnet_not_haiku() -> None:
    # Invariant #1: published content requires Sonnet quality.
    assert DraftGeneratorAI.model == "claude-sonnet-4-6"
    assert ANTHROPIC_MODEL_SONNET == "claude-sonnet-4-6"
    assert "haiku" not in DraftGeneratorAI.model


def test_system_context_carries_source_only_constraint() -> None:
    # Invariant #5: the source-only constraint MUST be in the system context.
    system = build_system_context("article")
    assert SOURCE_ONLY_MARKER in system
    assert "ORYX" in system
    assert "article" in system  # the format is named in Layer 1


def test_prompt_includes_objects_format_and_instructions() -> None:
    system, user = build_generation_prompt(
        objects=[_obj(headline="Zentech raised $5B")],
        format="tweet_thread",
        instructions="Focus on the macro angle",
    )
    # Layer 1 lives in system; Layers 2-4 in the user message.
    assert SOURCE_ONLY_MARKER in system
    assert "tweet_thread" in user
    assert "Zentech raised $5B" in user  # source headline present
    assert "raised $5B" in user  # key fact rendered
    assert "Focus on the macro angle" in user  # analyst instructions (Layer 4)


def test_prompt_handles_no_objects() -> None:
    system, user = build_generation_prompt(
        objects=[], format="article", instructions=None
    )
    assert SOURCE_ONLY_MARKER in system
    assert "(none provided)" in user
