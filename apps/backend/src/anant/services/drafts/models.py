"""Drafts domain entities + generation constants — frozen, no SQLAlchemy."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

# Bump when the model, the system context, or the prompt structure changes.
# Stored on content_drafts.generation_version so an analyst can tell which
# generation produced a draft and request a fresh one. Existing drafts are
# NEVER auto-regenerated on a version bump (analyst-triggered only).
GENERATION_MODEL_VERSION = 1

# The content formats an analyst can request. Mirrors content_format_enum and
# packages/shared-types/src/drafts.ts ContentFormat.
CONTENT_FORMATS: tuple[str, ...] = (
    "tweet_thread",
    "linkedin_post",
    "newsletter_section",
    "article",
    "report_summary",
    "custom",
)

# Per-format shaping guidance injected into the prompt (Layer 2). Wave A has no
# templates yet (Wave B adds content_templates); these are the built-in defaults.
FORMAT_GUIDANCE: dict[str, str] = {
    "tweet_thread": (
        "A connected thread of tweets. Each tweet must be 280 characters or "
        "fewer. Number them (1/n, 2/n, ...)."
    ),
    "linkedin_post": (
        "A single long-form LinkedIn post, 3000 characters or fewer, "
        "professional tone, no hashtag spam."
    ),
    "newsletter_section": (
        "An email-newsletter section: a short bold header followed by two to "
        "four tight paragraphs."
    ),
    "article": (
        "A long-form article, roughly 1000-5000 words, with a lede and clearly "
        "delineated sections."
    ),
    "report_summary": (
        "A structured executive summary, 200-500 words, leading with the "
        "bottom line."
    ),
    "custom": (
        "Free-form. Follow the analyst instructions for length, tone, and "
        "structure."
    ),
}


@dataclass(frozen=True)
class ObjectSnapshot:
    """Read-only projection of an intelligence object for prompt building.

    Only the fields the generator is permitted to ground content in. The
    generator never sees raw claims, evidence, or intake items (the Phase 5
    boundary: content is sourced exclusively through intelligence objects).
    """

    id: uuid.UUID
    headline: str
    epistemic_type: str
    confidence_score: float | None
    key_facts: dict[str, Any]


@dataclass(frozen=True)
class GeneratedDraft:
    content: str
    word_count: int
    token_count: int
