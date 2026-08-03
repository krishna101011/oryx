"""Citation provenance for published content (post-freeze patch to Phase 5).

Every published piece carries visible provenance back to the verified
intelligence it came from — proportional to what each channel's format can hold.

The data is the Wave A `draft_citations` edge (a draft → the
`intelligence_objects` it drew from); this module only READS it. `load_draft_citations`
is the publishing service's richer view of that same edge (headline + tier +
epistemic type, strongest first) — it does not duplicate the drafts service's
`list_citation_object_ids` (which returns bare ids in insertion order).

Confidence tiers are NOT a new scheme: `_confidence_tier` reuses the canonical
confidence-band thresholds (`oryx.shared.types.CONFIDENCE_BAND_THRESHOLDS`,
mirrored by `scoring.ts::confidenceBand`) — same labels, same boundaries.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import literal

from oryx.core.models import (
    DraftCitation,
    IntelligenceObject,
    PublicationCitation,
    PublicPageCitation,
)
from oryx.services.publishing.channels.formatting import thread_segments
from oryx.shared.types import CONFIDENCE_BAND_THRESHOLDS, PublishChannel

# Mirrors TwitterXChannel._MAX_TWEET — the per-segment ceiling we must not push a
# tweet over when appending a citation footer.
_MAX_TWEET = 280


@dataclass(frozen=True)
class CitationSummary:
    headline: str
    confidence_tier: str  # one of the existing confidence-band labels
    epistemic_type: str


def _confidence_tier(score: float | None) -> str:
    """Bucket a confidence score into the canonical band label.

    Identical logic to `scoring.ts::confidenceBand` / the Python band thresholds
    in `oryx.shared.types` — deliberately NOT a second tier system.
    """
    if score is None:
        return "unscored"
    for band, floor in CONFIDENCE_BAND_THRESHOLDS:
        if score >= floor:
            return band
    return "minimal"


async def load_draft_citations(
    draft_id: uuid.UUID, session: AsyncSession
) -> list[CitationSummary]:
    """The draft's citations as display summaries, strongest source first.

    Joins `draft_citations` → `intelligence_objects` (the verified, public-facing
    layer — never raw claims/evidence) and orders by confidence_score DESC.
    """
    result = await session.execute(
        select(
            IntelligenceObject.headline,
            IntelligenceObject.confidence_score,
            IntelligenceObject.epistemic_type,
        )
        .join(
            DraftCitation,
            DraftCitation.intelligence_object_id == IntelligenceObject.id,
        )
        .where(DraftCitation.draft_id == draft_id)
        .order_by(IntelligenceObject.confidence_score.desc())
    )
    return [
        CitationSummary(
            headline=row.headline,
            confidence_tier=_confidence_tier(row.confidence_score),
            epistemic_type=row.epistemic_type,
        )
        for row in result.all()
    ]


async def snapshot_citations(
    session: AsyncSession, *, publication_id: uuid.UUID, draft_id: uuid.UUID
) -> None:
    """Snapshot the draft's cited intelligence objects into
    publication_citations — headline, epistemic_type, confidence_score and
    scoring_version AS OF THIS TRANSACTION.

    Called by the engine inside the SAME transaction that inserts the pending
    publication row (never committed separately), so a publication cannot
    exist without its provenance snapshot. A single INSERT ... FROM SELECT
    reads the live values and writes the snapshot atomically; ON CONFLICT DO
    NOTHING on the composite PK makes engine retries (which re-enter the
    ensure_pending transaction) no-ops that preserve the ORIGINAL snapshot.
    """
    sel = (
        select(
            literal(publication_id),
            DraftCitation.intelligence_object_id,
            IntelligenceObject.headline,
            IntelligenceObject.epistemic_type,
            IntelligenceObject.confidence_score,
            IntelligenceObject.scoring_version,
        )
        .join(
            IntelligenceObject,
            IntelligenceObject.id == DraftCitation.intelligence_object_id,
        )
        .where(DraftCitation.draft_id == draft_id)
    )
    stmt = pg_insert(PublicationCitation).from_select(
        [
            "publication_id",
            "intelligence_object_id",
            "headline",
            "epistemic_type",
            "confidence_score",
            "scoring_version",
        ],
        sel,
    ).on_conflict_do_nothing(
        index_elements=["publication_id", "intelligence_object_id"]
    )
    await session.execute(stmt)


async def snapshot_citations_to_public_page(
    session: AsyncSession, *, public_page_id: uuid.UUID, draft_id: uuid.UUID
) -> None:
    """Same shape and same guarantees as `snapshot_citations` above, targeting
    public_page_citations instead of publication_citations (Public Reader
    Rev 1, §6). Called by the engine in the SAME transaction as the
    public_pages row insert, so a public page can never exist without its
    provenance snapshot. ON CONFLICT DO NOTHING on the composite PK makes a
    retried create() call a no-op that preserves the ORIGINAL snapshot —
    identical idempotency shape to the publication_citations sibling."""
    sel = (
        select(
            literal(public_page_id),
            DraftCitation.intelligence_object_id,
            IntelligenceObject.headline,
            IntelligenceObject.epistemic_type,
            IntelligenceObject.confidence_score,
            IntelligenceObject.scoring_version,
        )
        .join(
            IntelligenceObject,
            IntelligenceObject.id == DraftCitation.intelligence_object_id,
        )
        .where(DraftCitation.draft_id == draft_id)
    )
    stmt = pg_insert(PublicPageCitation).from_select(
        [
            "public_page_id",
            "intelligence_object_id",
            "headline",
            "epistemic_type",
            "confidence_score",
            "scoring_version",
        ],
        sel,
    ).on_conflict_do_nothing(
        index_elements=["public_page_id", "intelligence_object_id"]
    )
    await session.execute(stmt)


def format_citation_footer(
    citations: list[CitationSummary],
    channel: PublishChannel,
    *,
    content: str = "",
) -> str:
    """The citation footer to append to a channel's content string.

    Returns "" when there are no citations (caller appends nothing), and "" for
    webhook (which carries citations as a structured field, never in content).

    `content` is only consulted for twitter_x, where the footer must not push the
    final tweet segment over 280 chars — in that case it is omitted entirely
    rather than truncated mid-citation.
    """
    if not citations:
        return ""

    n = len(citations)

    if channel == "twitter_x":
        footer = f"\n\n— {n} verified source" + ("" if n == 1 else "s")
        segments = thread_segments(content, _MAX_TWEET) or [content]
        final = segments[-1]
        if len(final) + len(footer) > _MAX_TWEET:
            return ""  # omit rather than overflow / truncate the final tweet
        return footer

    if channel in ("notion", "export"):
        lines = [
            f"- {c.headline} ({c.confidence_tier}, {c.epistemic_type})"
            for c in citations
        ]
        return "\n\n## Sources\n" + "\n".join(lines)

    if channel == "webhook":
        return ""  # webhook carries citations as a separate JSON field

    # linkedin / email_newsletter (and any other prose channel): a short list
    # capped at 3, with an overflow line when more exist.
    shown = citations[:3]
    lines = [f"• {c.headline} ({c.confidence_tier})" for c in shown]
    if n > 3:
        lines.append(f"+ {n - 3} more verified source(s)")
    return "\n\nSources:\n" + "\n".join(lines)
