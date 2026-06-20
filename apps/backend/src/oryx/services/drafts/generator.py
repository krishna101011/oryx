"""DraftGeneratorAI — turns verified intelligence objects into prose.

Model: Claude SONNET, not Haiku. Phase 5 publishes content; prose quality is the
product, so the generation step pays for Sonnet (blueprint §9.1 / ADR-038).

Self-contained Anthropic client: Phase 5 keeps its own Sonnet call rather than
importing Phase 4's Haiku helper, so the content layer has no import dependency
on the claims pipeline. Vendor errors map onto the shared ProviderError taxonomy,
and the call runs behind the shared AI circuit breaker (call_type
"draft_generator").

The generation prompt has the four-layer shape from blueprint §9.2. Layer 1 — the
system context — carries the NON-NEGOTIABLE constraint that the model writes ONLY
from the provided intelligence objects. That constraint is what separates ORYX
content from generic AI writing; SOURCE_ONLY_MARKER is asserted by a unit test.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oryx.config import get_settings
from oryx.core.ai_provider import get_ai_provider
from oryx.core.logging import get_logger
from oryx.services.drafts.models import (
    FORMAT_GUIDANCE,
    GENERATION_MODEL_VERSION,
    GeneratedDraft,
    ObjectSnapshot,
)

logger = get_logger(__name__)

# Sonnet — quality over speed for published prose (ADR-038).
ANTHROPIC_MODEL_SONNET = "claude-sonnet-4-6"

GENERATION_MAX_TOKENS = 4096
GENERATION_TEMPERATURE = 0.4

# Layer 1 — system context. NON-NEGOTIABLE: the source-only constraint MUST be
# present verbatim (test_generation_prompt asserts SOURCE_ONLY_MARKER appears in
# the system string). This is invariant #5 of the Wave A contract.
SOURCE_ONLY_MARKER = "write ONLY from the provided intelligence objects"

SYSTEM_CONTEXT_TEMPLATE = (
    "You are the ORYX content generation system. You write verified financial "
    "intelligence as {format_label}. You {marker}. You do not introduce facts, "
    "claims, figures, company names, or dates that are not present in the source "
    "material. You never assert more certainty than the provided confidence "
    "scores justify. You cite your sources by referring to the intelligence "
    "object headlines. If the source material is insufficient to fill the "
    "requested format, say so plainly rather than inventing content."
)


def build_system_context(format: str) -> str:
    label = format.replace("_", " ")
    return SYSTEM_CONTEXT_TEMPLATE.format(format_label=label, marker=SOURCE_ONLY_MARKER)


def _fact_str(fact: Any) -> str:
    """Render one key_fact value. Composition stores facts as
    {predicate, object, epistemicType, confidence}; fall back to str()."""
    if isinstance(fact, dict):
        predicate = fact.get("predicate")
        obj = fact.get("object")
        if predicate or obj:
            return " ".join(str(x) for x in (predicate, obj) if x is not None)
    return str(fact)


def _render_object(obj: ObjectSnapshot) -> str:
    confidence = (
        f"{obj.confidence_score:.2f}" if obj.confidence_score is not None else "n/a"
    )
    lines = [
        f"- Headline: {obj.headline}",
        f"  Epistemic type: {obj.epistemic_type}",
        f"  Confidence: {confidence}",
    ]
    if obj.key_facts:
        lines.append("  Key facts:")
        for subject, fact in obj.key_facts.items():
            lines.append(f"    - {subject}: {_fact_str(fact)}")
    return "\n".join(lines)


def build_generation_prompt(
    *, objects: list[ObjectSnapshot], format: str, instructions: str | None
) -> tuple[str, str]:
    """Build the (system, user) pair. Layer 1 → system; Layers 2-4 → user."""
    system = build_system_context(format)

    parts: list[str] = []
    # Layer 2 — format specification.
    parts.append(f"FORMAT: {format}")
    parts.append(
        f"FORMAT GUIDANCE: {FORMAT_GUIDANCE.get(format, FORMAT_GUIDANCE['custom'])}"
    )
    # Layer 3 — source material (the only ground truth).
    parts.append("\nINTELLIGENCE OBJECTS (the only source material):")
    if objects:
        parts.append("\n\n".join(_render_object(o) for o in objects))
    else:
        parts.append("(none provided)")
    # Layer 4 — analyst instructions (optional).
    if instructions and instructions.strip():
        parts.append(f"\nANALYST INSTRUCTIONS: {instructions.strip()}")
    parts.append("\nWrite the content now. Output only the content itself.")
    return system, "\n".join(parts)


@dataclass(frozen=True)
class _SonnetResult:
    text: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


async def _call_sonnet(*, system: str, user_content: str) -> _SonnetResult:
    """Provider-agnostic generation call. Routes to AnthropicProvider (Sonnet) or
    OllamaProvider based on AI_PROVIDER setting. Vendor errors map onto ProviderError
    so the circuit breaker / drainer retry policy applies unchanged."""
    settings = get_settings()
    provider = get_ai_provider(settings, model=ANTHROPIC_MODEL_SONNET, timeout=120.0)
    text, total_tokens = await provider.complete(
        system=system,
        user=user_content,
        max_tokens=GENERATION_MAX_TOKENS,
        temperature=GENERATION_TEMPERATURE,
    )
    return _SonnetResult(text=text, input_tokens=0, output_tokens=total_tokens)


def _word_count(text: str) -> int:
    return len(text.split())


class DraftGeneratorAI:
    """Stateless. One instance per call is fine."""

    version = GENERATION_MODEL_VERSION
    model = ANTHROPIC_MODEL_SONNET

    async def generate(
        self,
        *,
        objects: list[ObjectSnapshot],
        format: str,
        instructions: str | None = None,
    ) -> GeneratedDraft:
        from oryx.core.ai_circuit_breaker import ai_circuit_breaker

        system, user = build_generation_prompt(
            objects=objects, format=format, instructions=instructions
        )
        result = await ai_circuit_breaker.call(
            "draft_generator",
            lambda: _call_sonnet(system=system, user_content=user),
        )
        content = result.text.strip()
        return GeneratedDraft(
            content=content,
            word_count=_word_count(content),
            token_count=result.total_tokens,
        )
