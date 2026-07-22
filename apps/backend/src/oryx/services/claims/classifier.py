"""EpistemicClassifierAI — types one claim along the epistemic spectrum.

Single-word output contract; anything outside the allowed set falls back
to 'claim' with requires_analyst_review=true (conservative default).
"""
from __future__ import annotations

from dataclasses import dataclass

from oryx.core.logging import get_logger
from oryx.services.claims.extractor import call_ai_provider

logger = get_logger(__name__)

CLASSIFIER_VERSION = 1

CLASSIFIER_MAX_TOKENS = 50
CLASSIFIER_TEMPERATURE = 0
CONTEXT_CHARS = 500

ALLOWED_TYPES = frozenset({"fact", "claim", "rumor", "speculation", "opinion"})

CLASSIFIER_SYSTEM_PROMPT = """\
You classify one extracted assertion along an epistemic spectrum.

Return ONLY one lowercase word from this set:
fact | claim | rumor | speculation | opinion

No explanation. No punctuation. No other output.

Definitions and conservative defaults:
- "fact" ONLY when the surrounding context contains an explicit
  primary-source signal (an official filing, regulator statement,
  company press release, court record, or named primary document).
- "opinion" ONLY when a named person is expressing a subjective view.
- Ambiguous between fact and claim -> answer "claim".
- Ambiguous between claim and rumor -> answer "rumor".
- Ambiguous between rumor and opinion -> answer "rumor".
"""


@dataclass(frozen=True)
class ClassificationResult:
    epistemic_type: str
    tokens_used: int
    requires_analyst_review: bool  # True when the model broke the contract


class EpistemicClassifierAI:
    """Stateless. One instance per handler invocation is fine."""

    version = CLASSIFIER_VERSION

    async def classify(self, claim_text: str, context: str) -> ClassificationResult:
        user_content = (
            f"Claim:\n{claim_text}\n\n"
            f"Context (start of source document):\n{context[:CONTEXT_CHARS]}"
        )
        # Wave B retrofit: same call, now behind the shared circuit breaker.
        from oryx.core.ai_circuit_breaker import ai_circuit_breaker, ai_quality_tracker

        result = await ai_circuit_breaker.call(
            "classifier",
            lambda: call_ai_provider(
                system=CLASSIFIER_SYSTEM_PROMPT,
                user_content=user_content,
                max_tokens=CLASSIFIER_MAX_TOKENS,
                temperature=CLASSIFIER_TEMPERATURE,
            ),
        )
        label = result.text.strip().lower()
        # A bad label is the same contract-violation class as unparseable JSON
        # (2026-07-22 ADR) — the classifier's contract is one allowed word.
        ai_quality_tracker.record_parse_outcome("classifier", ok=label in ALLOWED_TYPES)
        if label not in ALLOWED_TYPES:
            logger.warning(
                "claims.classifier_bad_label",
                extra={"label_prefix": label[:40]},
            )
            return ClassificationResult(
                epistemic_type="claim",
                tokens_used=result.total_tokens,
                requires_analyst_review=True,
            )
        return ClassificationResult(
            epistemic_type=label,
            tokens_used=result.total_tokens,
            requires_analyst_review=False,
        )
