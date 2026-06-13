"""ClaimExtractorAI — extracts atomic claims from normalized item text.

Calls the Anthropic Messages API directly over httpx (no SDK dependency —
pyproject ships httpx only). The shared `call_anthropic` helper here is
also used by classifier.py.

Budget gate: callers check the workspace ledger BEFORE invoking extract();
on exhaustion the extraction is deferred (transient retry), because a
skipped extraction produces no claim rows to flag for review — see
service.py for the policy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from anant.config import get_settings
from anant.core.logging import get_logger
from anant.services.claims.models import ClaimTriple
from anant.services.intake.providers.errors import ProviderError, ProviderErrorKind

logger = get_logger(__name__)

EXTRACTOR_VERSION = 1

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

EXTRACTOR_MAX_TOKENS = 800
EXTRACTOR_TEMPERATURE = 0
MAX_CLAIMS_PER_ITEM = 8
# Cost guard: intake bodies can be 100KB+ of newsletter HTML-derived text.
# Past this window the marginal claim yield is ~zero but the input-token
# spend is real. (Operational cap, not part of the extraction contract.)
EXTRACTOR_INPUT_MAX_CHARS = 20_000

EXTRACTOR_SYSTEM_PROMPT = """\
You extract atomic factual assertions from financial-intelligence text.

Rules:
- Extract each assertion as a subject/predicate/object triple.
- Output ONLY valid JSON. No prose, no markdown, no code fences.
- Return a JSON array of objects with exactly these keys:
  "subject", "predicate", "object" (string or null),
  "text" (the full claim sentence).
- Extract at most 8 claims. If the text asserts nothing, return [].
- Skip subjective language, questions, predictions framed as questions,
  and anything that is not an assertion of fact.

Output format (exactly this shape):
[
  {
    "subject": "Apple Inc",
    "predicate": "reported revenue of",
    "object": "$94.9 billion",
    "text": "Apple Inc reported revenue of $94.9 billion in Q1 2024."
  }
]
"""


@dataclass(frozen=True)
class AnthropicResult:
    text: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


async def call_anthropic(
    *,
    system: str,
    user_content: str,
    max_tokens: int,
    temperature: float,
) -> AnthropicResult:
    """One Messages-API call. Vendor errors map onto the existing
    ProviderError taxonomy so the drainer's retry policy applies."""
    settings = get_settings()
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ProviderError(
            kind=ProviderErrorKind.AUTH,
            message="ANTHROPIC_API_KEY is not configured",
        )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
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
    return AnthropicResult(
        text=text,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )


@dataclass(frozen=True)
class ExtractionResult:
    triples: list[ClaimTriple]
    tokens_used: int
    parse_failed: bool  # True → caller flags the item for analyst review


class ClaimExtractorAI:
    """Stateless. One instance per handler invocation is fine."""

    version = EXTRACTOR_VERSION

    async def extract(self, body_text: str) -> ExtractionResult:
        # Wave B retrofit: same call, now behind the shared circuit breaker.
        from anant.core.ai_circuit_breaker import ai_circuit_breaker

        result = await ai_circuit_breaker.call(
            "extractor",
            lambda: call_anthropic(
                system=EXTRACTOR_SYSTEM_PROMPT,
                user_content=body_text[:EXTRACTOR_INPUT_MAX_CHARS],
                max_tokens=EXTRACTOR_MAX_TOKENS,
                temperature=EXTRACTOR_TEMPERATURE,
            ),
        )
        triples = _parse_triples(result.text)
        if triples is None:
            # Malformed model output is not a delivery failure: log, flag,
            # and move on with zero claims (spec: do not fail the event).
            logger.warning(
                "claims.extractor_parse_failed",
                extra={"output_prefix": result.text[:120]},
            )
            return ExtractionResult(
                triples=[], tokens_used=result.total_tokens, parse_failed=True
            )
        return ExtractionResult(
            triples=triples[:MAX_CLAIMS_PER_ITEM],
            tokens_used=result.total_tokens,
            parse_failed=False,
        )


def _strip_code_fence(raw: str) -> str:
    """Salvage the most common contract slip: a fenced JSON block."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1 and stripped.endswith("```"):
            return stripped[first_newline + 1 : -3].strip()
    return stripped


def _parse_triples(raw: str) -> list[ClaimTriple] | None:
    """None means unparseable; [] is a valid zero-claim result."""
    try:
        parsed = json.loads(_strip_code_fence(raw))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, list):
        return None
    triples: list[ClaimTriple] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            return None
        subject = entry.get("subject")
        predicate = entry.get("predicate")
        text = entry.get("text")
        object_ = entry.get("object")
        if not (isinstance(subject, str) and subject.strip()):
            return None
        if not (isinstance(predicate, str) and predicate.strip()):
            return None
        if not (isinstance(text, str) and text.strip()):
            return None
        if object_ is not None and not isinstance(object_, str):
            return None
        triples.append(
            ClaimTriple(
                subject=subject.strip(),
                predicate=predicate.strip(),
                object=object_.strip() if isinstance(object_, str) else None,
                text=text.strip(),
            )
        )
    return triples
