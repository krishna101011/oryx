"""EvidenceLinkerAI — classifies corpus candidates as evidence for a claim.

ONE Anthropic call per claim, all candidates batched into the prompt —
never one call per candidate. Candidates are identified to the model by
their intake_item_id; any id the model returns that was not in the
candidate set is discarded (hallucination guard).

Type→relationship mapping is enforced in code after parsing; the prompt
states it, the parser guarantees it.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from oryx.core.ai_circuit_breaker import ai_circuit_breaker
from oryx.core.logging import get_logger
from oryx.services.claims.extractor import call_anthropic
from oryx.services.evidence.models import (
    EVIDENCE_TYPES,
    TYPE_TO_RELATIONSHIP,
    CandidateItem,
    LinkResult,
)

logger = get_logger(__name__)

LINKER_VERSION = 1

LINKER_MAX_TOKENS = 150
LINKER_TEMPERATURE = 0
CIRCUIT_CALL_TYPE = "evidence_linker"

LINKER_SYSTEM_PROMPT = """\
You judge whether candidate documents are evidence for a claim.

For EVERY candidate, output one judgment object. Output ONLY a valid JSON
array — no prose, no markdown, no code fences.

Each object has exactly these keys:
  "intake_item_id": the candidate's id, copied verbatim
  "evidence_type": one of
      corroboration | contradiction | context |
      primary_source | secondary_source | inference
  "relationship": one of supports | contradicts | contextualizes
      (contradiction -> contradicts;
       corroboration/primary_source/secondary_source -> supports;
       context/inference -> contextualizes)
  "strength": number from 0.0 to 1.0
  "include": boolean — false when the candidate is not actually
      relevant evidence for this claim

Output format (exactly this shape):
[
  {
    "intake_item_id": "uuid-string",
    "evidence_type": "corroboration",
    "relationship": "supports",
    "strength": 0.7,
    "include": true
  }
]
"""


@dataclass(frozen=True)
class LinkingResult:
    results: list[LinkResult]
    tokens_used: int
    parse_failed: bool  # True → caller flags the claim for analyst review


class EvidenceLinkerAI:
    """Stateless. One instance per handler invocation is fine."""

    version = LINKER_VERSION

    async def link(
        self, claim_text: str, candidates: list[CandidateItem]
    ) -> LinkingResult:
        user_content = _build_user_content(claim_text, candidates)
        result = await ai_circuit_breaker.call(
            CIRCUIT_CALL_TYPE,
            lambda: call_anthropic(
                system=LINKER_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=LINKER_MAX_TOKENS,
                temperature=LINKER_TEMPERATURE,
            ),
        )
        allowed_ids = {c.intake_item_id for c in candidates}
        parsed = _parse_results(result.text, allowed_ids=allowed_ids)
        if parsed is None:
            logger.warning(
                "evidence.linker_parse_failed",
                extra={"output_prefix": result.text[:120]},
            )
            return LinkingResult(
                results=[], tokens_used=result.total_tokens, parse_failed=True
            )
        return LinkingResult(
            results=parsed, tokens_used=result.total_tokens, parse_failed=False
        )


def _build_user_content(claim_text: str, candidates: list[CandidateItem]) -> str:
    lines = [f"Claim:\n{claim_text}", "", "Candidates:"]
    for c in candidates:
        subject = c.subject or "(no subject)"
        lines.append(
            f"- intake_item_id: {c.intake_item_id}\n"
            f"  subject: {subject}\n"
            f"  excerpt: {c.body_text_excerpt}"
        )
    return "\n".join(lines)


def _strip_code_fence(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1 and stripped.endswith("```"):
            return stripped[first_newline + 1 : -3].strip()
    return stripped


def _parse_results(
    raw: str, *, allowed_ids: set[uuid.UUID]
) -> list[LinkResult] | None:
    """None = unparseable. Individual bad entries are skipped, not fatal:
    invalid evidence_type → skip; hallucinated id → skip; wrong
    relationship → corrected silently; strength → clamped to [0, 1]."""
    try:
        parsed = json.loads(_strip_code_fence(raw))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, list):
        return None

    out: list[LinkResult] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            return None
        try:
            item_id = uuid.UUID(str(entry.get("intake_item_id")))
        except (ValueError, TypeError):
            continue  # malformed id → skip the candidate
        if item_id not in allowed_ids:
            continue  # hallucinated id → never link it

        evidence_type = entry.get("evidence_type")
        if evidence_type not in EVIDENCE_TYPES:
            continue  # invalid type → skip per spec

        # Mapping enforced in code regardless of what the model said.
        relationship = TYPE_TO_RELATIONSHIP[evidence_type]

        raw_strength = entry.get("strength")
        if not isinstance(raw_strength, (int, float)) or isinstance(raw_strength, bool):
            continue
        strength = min(1.0, max(0.0, float(raw_strength)))

        out.append(
            LinkResult(
                intake_item_id=item_id,
                evidence_type=evidence_type,
                relationship=relationship,
                strength=strength,
                include=bool(entry.get("include")),
            )
        )
    return out
