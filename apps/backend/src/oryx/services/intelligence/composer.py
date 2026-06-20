"""ObjectComposer — the fan-in. N non-superseded claims for one intake item
become one scored intelligence object. No AI: the headline is intake-derived
plain text and key_facts is structured extraction, never prose.

The type-selection and scoring are pure functions (unit-tested); compose()
does the reads and assembles the result.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    Claim,
    ConflictRecord,
    IntakeItemNormalized,
    VerificationRun,
)
from oryx.core.scoring_version import CURRENT_SCORING_VERSION
from oryx.services.intelligence.models import (
    COMPOSITION_CEILINGS,
    COMPOSITION_HIERARCHY,
    UNCLASSIFIED_AS,
    IntelligenceObjectResult,
)

# Weighted-minimum weights (§STEP2.5): the floor dominates, the mean tempers it.
W_MIN = 0.60
W_MEAN = 0.40


def select_epistemic_type(types: list[str]) -> str:
    """Most uncertain (earliest in the hierarchy) type among the claims.
    unclassified counts as rumor. Empty → 'unclassified'."""
    if not types:
        return "unclassified"
    best_idx = len(COMPOSITION_HIERARCHY)
    for t in types:
        mapped = UNCLASSIFIED_AS if t == "unclassified" else t
        idx = (
            COMPOSITION_HIERARCHY.index(mapped)
            if mapped in COMPOSITION_HIERARCHY
            else len(COMPOSITION_HIERARCHY)
        )
        best_idx = min(best_idx, idx)
    if best_idx >= len(COMPOSITION_HIERARCHY):
        return "unclassified"
    return COMPOSITION_HIERARCHY[best_idx]


def compute_score(scores: list[float], epistemic_type: str) -> float | None:
    """raw = min*0.60 + mean*0.40, capped at the epistemic ceiling. Empty → None."""
    if not scores:
        return None
    raw = min(scores) * W_MIN + (sum(scores) / len(scores)) * W_MEAN
    ceiling = COMPOSITION_CEILINGS.get(epistemic_type, COMPOSITION_CEILINGS["rumor"])
    return min(raw, ceiling)


def _headline(normalized: IntakeItemNormalized | None) -> str:
    if normalized is not None and normalized.subject and normalized.subject.strip():
        return normalized.subject
    if (
        normalized is not None
        and normalized.sender_label
        and normalized.sender_label.strip()
    ):
        return normalized.sender_label
    return "Untitled"


def _status(
    claims: list[Claim],
    runs_by_claim: dict[uuid.UUID, VerificationRun],
    *,
    has_open_conflict: bool,
) -> str:
    if has_open_conflict:
        return "contested"
    if claims and all(
        (runs_by_claim.get(c.id) is not None and runs_by_claim[c.id].outcome == "verified")
        for c in claims
    ):
        return "verified"
    return "unverified"


class ObjectComposer:
    async def compose(
        self,
        *,
        intake_item_id: uuid.UUID,
        workspace_id: uuid.UUID,
        session: AsyncSession,
    ) -> IntelligenceObjectResult:
        claims = list(
            (
                await session.execute(
                    select(Claim).where(
                        Claim.workspace_id == workspace_id,
                        Claim.intake_item_id == intake_item_id,
                        Claim.superseded_by.is_(None),
                    )
                )
            ).scalars().all()
        )
        claim_ids = [c.id for c in claims]

        # Latest complete run per claim (started_at DESC; verification keeps one
        # complete run per claim, so this is unambiguous in practice).
        runs_by_claim: dict[uuid.UUID, VerificationRun] = {}
        if claim_ids:
            rows = (
                await session.execute(
                    select(VerificationRun)
                    .where(
                        VerificationRun.claim_id.in_(claim_ids),
                        VerificationRun.status == "complete",
                    )
                    .order_by(VerificationRun.started_at.desc())
                )
            ).scalars().all()
            for r in rows:
                runs_by_claim.setdefault(r.claim_id, r)

        epistemic_type = select_epistemic_type([c.epistemic_type for c in claims])
        scores = [
            r.confidence_score
            for r in runs_by_claim.values()
            if r.confidence_score is not None
        ]
        confidence = compute_score(scores, epistemic_type)

        normalized = await session.get(IntakeItemNormalized, intake_item_id)
        headline = _headline(normalized)

        key_facts: dict[str, Any] = {}
        for c in claims:
            run = runs_by_claim.get(c.id)
            key_facts[c.subject] = {
                "predicate": c.predicate,
                "object": c.object,
                "epistemicType": c.epistemic_type,
                "confidence": run.confidence_score if run else None,
            }

        open_conflicts: list[ConflictRecord] = []
        if claim_ids:
            open_conflicts = list(
                (
                    await session.execute(
                        select(ConflictRecord).where(
                            ConflictRecord.workspace_id == workspace_id,
                            ConflictRecord.status == "open",
                            or_(
                                ConflictRecord.claim_a_id.in_(claim_ids),
                                ConflictRecord.claim_b_id.in_(claim_ids),
                            ),
                        )
                    )
                ).scalars().all()
            )
        conflict_ids = [cr.id for cr in open_conflicts]

        status = _status(
            claims, runs_by_claim, has_open_conflict=bool(open_conflicts)
        )

        return IntelligenceObjectResult(
            epistemic_type=epistemic_type,
            confidence_score=confidence,
            verification_status=status,
            claim_ids=claim_ids,
            conflict_ids=conflict_ids,
            key_facts=key_facts,
            headline=headline,
            scoring_version=CURRENT_SCORING_VERSION,
        )
