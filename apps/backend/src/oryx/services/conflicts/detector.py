"""ConflictDetectorAI — decides whether two same-subject claims conflict.

ONE Anthropic call per claim pair. Used only on PATH B (no explicit
contradiction evidence link already exists between the claims); PATH A
creates the conflict deterministically without any AI.

Safety posture (mirrors the linker): an unparseable / malformed response
yields "no conflict" rather than a spurious record. An unrecognized
conflict_type is coerced to the neutral default.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from oryx.core.ai_circuit_breaker import ai_circuit_breaker, ai_quality_tracker
from oryx.core.logging import get_logger
from oryx.services.claims.extractor import call_ai_provider
from oryx.services.conflicts.models import (
    CONFLICT_TYPES,
    DEFAULT_CONFLICT_TYPE,
    ConflictResult,
)

logger = get_logger(__name__)

DETECTOR_VERSION = 1
DETECTOR_MAX_TOKENS = 200
DETECTOR_TEMPERATURE = 0
CIRCUIT_CALL_TYPE = "conflict_detector"

NO_CONFLICT = ConflictResult(
    is_conflict=False, conflict_type=DEFAULT_CONFLICT_TYPE, severity=0.0, reasoning=""
)

DETECTOR_SYSTEM_PROMPT = """\
You decide whether two claims about the same subject are in conflict — that is,
whether their predicates are mutually exclusive (they cannot both be true).

Output ONLY a valid JSON object — no prose, no markdown, no code fences — with
exactly these keys:
  "is_conflict": boolean
  "conflict_type": one of
      direct_contradiction | factual_disagreement |
      temporal_inconsistency | scope_difference
  "severity": number from 0.0 to 1.0 (how strongly they exclude each other)
  "reasoning": one sentence, max

If the two claims can both be true (different scope, complementary, or simply
unrelated predicates), return is_conflict false.

Output format (exactly this shape):
{
  "is_conflict": true,
  "conflict_type": "direct_contradiction",
  "severity": 0.85,
  "reasoning": "one sentence max"
}
"""


@dataclass(frozen=True)
class DetectionResult:
    result: ConflictResult
    tokens_used: int
    # True when the model output was unparseable and NO_CONFLICT is a fallback,
    # not a judgment — the caller emits the observational parse-failed event.
    # The "no conflict" outcome itself is unchanged (safety posture above).
    parse_failed: bool = False


class ConflictDetectorAI:
    """Stateless. One instance per handler invocation is fine."""

    version = DETECTOR_VERSION

    async def detect(
        self,
        *,
        subject: str,
        a_predicate: str,
        a_object: str | None,
        b_predicate: str,
        b_object: str | None,
    ) -> DetectionResult:
        user_content = _build_user_content(
            subject, a_predicate, a_object, b_predicate, b_object
        )
        ai = await ai_circuit_breaker.call(
            CIRCUIT_CALL_TYPE,
            lambda: call_ai_provider(
                system=DETECTOR_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=DETECTOR_MAX_TOKENS,
                temperature=DETECTOR_TEMPERATURE,
            ),
        )
        parsed = _parse(ai.text)
        ai_quality_tracker.record_parse_outcome(
            CIRCUIT_CALL_TYPE, ok=parsed is not None
        )
        if parsed is None:
            logger.warning(
                "conflicts.detector_parse_failed",
                extra={"output_prefix": ai.text[:120]},
            )
            return DetectionResult(
                result=NO_CONFLICT, tokens_used=ai.total_tokens, parse_failed=True
            )
        return DetectionResult(result=parsed, tokens_used=ai.total_tokens)


def _build_user_content(
    subject: str,
    a_predicate: str,
    a_object: str | None,
    b_predicate: str,
    b_object: str | None,
) -> str:
    return (
        f"Subject: {subject}\n\n"
        f"Claim A predicate: {a_predicate}\n"
        f"Claim A object: {a_object or '(none)'}\n\n"
        f"Claim B predicate: {b_predicate}\n"
        f"Claim B object: {b_object or '(none)'}"
    )


def _strip_code_fence(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1 and stripped.endswith("```"):
            return stripped[first_newline + 1 : -3].strip()
    return stripped


def _parse(raw: str) -> ConflictResult | None:
    """None = unparseable (caller treats as no conflict). An invalid
    conflict_type is coerced to the default; severity is clamped to [0, 1]."""
    try:
        parsed = json.loads(_strip_code_fence(raw))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None

    is_conflict = bool(parsed.get("is_conflict"))
    if not is_conflict:
        return NO_CONFLICT

    conflict_type = parsed.get("conflict_type")
    if conflict_type not in CONFLICT_TYPES:
        conflict_type = DEFAULT_CONFLICT_TYPE

    raw_severity = parsed.get("severity")
    if not isinstance(raw_severity, (int, float)) or isinstance(raw_severity, bool):
        severity = 0.5
    else:
        severity = min(1.0, max(0.0, float(raw_severity)))

    reasoning = parsed.get("reasoning")
    reasoning = reasoning.strip() if isinstance(reasoning, str) else ""

    return ConflictResult(
        is_conflict=True,
        conflict_type=conflict_type,
        severity=severity,
        reasoning=reasoning[:280],
    )
