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

import httpx

from anant.config import get_settings
from anant.core.logging import get_logger
from anant.services.drafts.models import (
    FORMAT_GUIDANCE,
    GENERATION_MODEL_VERSION,
    GeneratedDraft,
    ObjectSnapshot,
)
from anant.services.intake.providers.errors import ProviderError, ProviderErrorKind

logger = get_logger(__name__)

# Sonnet — quality over speed for published prose (ADR-038).
ANTHROPIC_MODEL_SONNET = "claude-sonnet-4-6"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

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
    """One Messages-API call on Sonnet. Vendor errors map onto ProviderError so
    the circuit breaker / drainer retry policy applies (Phase 4's taxonomy)."""
    settings = get_settings()
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message="ANTHROPIC_API_KEY is not configured",
        )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL_SONNET,
                    "max_tokens": GENERATION_MAX_TOKENS,
                    "temperature": GENERATION_TEMPERATURE,
                    "system": system,
                    "messages": [{"role": "user", "content": user_content}],
                },
            )
    except httpx.HTTPError as e:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"Anthropic API unreachable: {e}",
        ) from e

    if resp.status_code == 401:
        raise ProviderError(
            kind=ProviderErrorKind.AUTH, message="Anthropic API key rejected"
        )
    if resp.status_code == 429:
        retry_after = resp.headers.get("retry-after")
        raise ProviderError(
            kind=ProviderErrorKind.RATE_LIMITED,
            message="Anthropic rate limit",
            retry_after_seconds=int(retry_after) if retry_after else None,
        )
    if resp.status_code >= 500:
        raise ProviderError(
            kind=ProviderErrorKind.TRANSIENT,
            message=f"Anthropic API {resp.status_code}",
        )
    if resp.status_code >= 400:
        raise ProviderError(
            kind=ProviderErrorKind.PERMANENT,
            message=f"Anthropic API {resp.status_code}: {resp.text[:200]}",
        )

    data: dict[str, Any] = resp.json()
    blocks = data.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    usage = data.get("usage") or {}
    return _SonnetResult(
        text=text,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )


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
        from anant.core.ai_circuit_breaker import ai_circuit_breaker

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
