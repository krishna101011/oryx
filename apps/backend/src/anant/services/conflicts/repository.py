"""Conflicts repository — DB operations only, no business rules."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import (
    Claim,
    ClaimEvidenceLink,
    ConflictRecord,
    Evidence,
    IntakeItem,
    SourceCredibilityRecord,
    VerificationAuditLog,
    VerificationRun,
    Workspace,
)

DEFAULT_ACCURACY = 0.5


class ConflictRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- cross-domain reads ----------------

    async def workspace_exists(self, workspace_id: uuid.UUID) -> bool:
        row = await self.db.get(Workspace, workspace_id)
        return row is not None and row.deleted_at is None

    async def get_claim(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> Claim | None:
        result = await self.db.execute(
            select(Claim).where(
                Claim.id == claim_id, Claim.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def get_intake_item(self, intake_item_id: uuid.UUID) -> IntakeItem | None:
        return await self.db.get(IntakeItem, intake_item_id)

    async def find_candidate_claims(
        self, *, workspace_id: uuid.UUID, subject: str, exclude_claim_id: uuid.UUID
    ) -> list[Claim]:
        """Same-subject, non-superseded claims that already have a completed
        verification run — the only claims worth comparing against."""
        has_complete_run = (
            exists()
            .where(VerificationRun.claim_id == Claim.id)
            .where(VerificationRun.status == "complete")
        )
        result = await self.db.execute(
            select(Claim).where(
                Claim.workspace_id == workspace_id,
                Claim.subject == subject,
                Claim.superseded_by.is_(None),
                Claim.id != exclude_claim_id,
                has_complete_run,
            )
        )
        return list(result.scalars().all())

    async def latest_confidence(self, claim_id: uuid.UUID) -> float | None:
        """confidence_score of the most recent COMPLETE run, or None."""
        result = await self.db.execute(
            select(VerificationRun.confidence_score)
            .where(
                VerificationRun.claim_id == claim_id,
                VerificationRun.status == "complete",
            )
            .order_by(VerificationRun.started_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None

    async def contradiction_link_strength(
        self,
        *,
        claim_a_id: uuid.UUID,
        claim_a_item_id: uuid.UUID,
        claim_b_id: uuid.UUID,
        claim_b_item_id: uuid.UUID,
    ) -> float | None:
        """Strength of an explicit 'contradicts' evidence link between the two
        claims' intake items (either direction), or None if there is none."""
        result = await self.db.execute(
            select(func.max(ClaimEvidenceLink.strength))
            .select_from(ClaimEvidenceLink)
            .join(Evidence, Evidence.id == ClaimEvidenceLink.evidence_id)
            .where(
                ClaimEvidenceLink.relationship == "contradicts",
                or_(
                    and_(
                        ClaimEvidenceLink.claim_id == claim_a_id,
                        Evidence.intake_item_id == claim_b_item_id,
                    ),
                    and_(
                        ClaimEvidenceLink.claim_id == claim_b_id,
                        Evidence.intake_item_id == claim_a_item_id,
                    ),
                ),
            )
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None

    async def evidence_type_counts(self, claim_id: uuid.UUID) -> dict[str, int]:
        """How many evidence links of each evidence_type back this claim."""
        result = await self.db.execute(
            select(Evidence.evidence_type, func.count())
            .select_from(ClaimEvidenceLink)
            .join(Evidence, Evidence.id == ClaimEvidenceLink.evidence_id)
            .where(ClaimEvidenceLink.claim_id == claim_id)
            .group_by(Evidence.evidence_type)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_source_accuracy(
        self, *, workspace_id: uuid.UUID, source_id: uuid.UUID
    ) -> float:
        result = await self.db.execute(
            select(SourceCredibilityRecord.accuracy_rate).where(
                SourceCredibilityRecord.workspace_id == workspace_id,
                SourceCredibilityRecord.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else DEFAULT_ACCURACY

    # ---------------- conflict_records ----------------

    async def insert_conflict(
        self,
        *,
        workspace_id: uuid.UUID,
        claim_a_id: uuid.UUID,
        claim_b_id: uuid.UUID,
        conflict_type: str,
        severity: float,
    ) -> ConflictRecord | None:
        """Insert with canonical ordering already applied by the caller.
        Returns the new row, or None when the pair already existed (idempotent
        re-delivery — ON CONFLICT DO NOTHING)."""
        stmt = (
            pg_insert(ConflictRecord)
            .values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                claim_a_id=claim_a_id,
                claim_b_id=claim_b_id,
                conflict_type=conflict_type,
                severity=severity,
                status="open",
            )
            .on_conflict_do_nothing(
                index_elements=["workspace_id", "claim_a_id", "claim_b_id"]
            )
            .returning(ConflictRecord.id)
        )
        new_id = (await self.db.execute(stmt)).scalar_one_or_none()
        if new_id is None:
            return None
        return await self.db.get(ConflictRecord, new_id)

    async def existing_conflict_partner_ids(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> set[uuid.UUID]:
        """Claim ids already paired with this claim in any conflict_record.
        Lets detection skip the AI call on re-delivery (idempotency saver)."""
        result = await self.db.execute(
            select(ConflictRecord.claim_a_id, ConflictRecord.claim_b_id).where(
                ConflictRecord.workspace_id == workspace_id,
                or_(
                    ConflictRecord.claim_a_id == claim_id,
                    ConflictRecord.claim_b_id == claim_id,
                ),
            )
        )
        partners: set[uuid.UUID] = set()
        for a, b in result.all():
            partners.add(b if a == claim_id else a)
        return partners

    async def get_conflict(
        self, *, workspace_id: uuid.UUID, conflict_id: uuid.UUID
    ) -> ConflictRecord | None:
        result = await self.db.execute(
            select(ConflictRecord).where(
                ConflictRecord.id == conflict_id,
                ConflictRecord.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_conflicts(
        self, *, workspace_id: uuid.UUID, status: str | None, limit: int = 50
    ) -> list[ConflictRecord]:
        stmt = select(ConflictRecord).where(
            ConflictRecord.workspace_id == workspace_id
        )
        if status is not None:
            stmt = stmt.where(ConflictRecord.status == status)
        stmt = stmt.order_by(ConflictRecord.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_open_conflicts(
        self, workspace_id: uuid.UUID
    ) -> list[ConflictRecord]:
        result = await self.db.execute(
            select(ConflictRecord)
            .where(
                ConflictRecord.workspace_id == workspace_id,
                ConflictRecord.status == "open",
            )
            .order_by(ConflictRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_pending_claims(self, workspace_id: uuid.UUID) -> list[Claim]:
        result = await self.db.execute(
            select(Claim)
            .where(
                Claim.workspace_id == workspace_id,
                Claim.requires_analyst_review.is_(True),
                Claim.superseded_by.is_(None),
            )
            .order_by(Claim.created_at.desc())
        )
        return list(result.scalars().all())

    async def resolve_conflict_system(
        self,
        *,
        conflict_id: uuid.UUID,
        winner_id: uuid.UUID,
        loser_id: uuid.UUID,
        note: str,
    ) -> None:
        now = datetime.now(UTC)
        await self.db.execute(
            update(ConflictRecord)
            .where(ConflictRecord.id == conflict_id)
            .values(
                status="resolved_system",
                resolved_by_kind="system",
                resolved_at=now,
                resolution_note=note,
            )
        )
        await self.set_superseded(loser_id=loser_id, winner_id=winner_id)

    async def resolve_conflict_analyst(
        self,
        *,
        conflict_id: uuid.UUID,
        status: str,
        account_id: uuid.UUID,
        note: str,
    ) -> None:
        await self.db.execute(
            update(ConflictRecord)
            .where(ConflictRecord.id == conflict_id)
            .values(
                status=status,
                resolved_by=account_id,
                resolved_by_kind="analyst",
                resolved_at=datetime.now(UTC),
                resolution_note=note,
            )
        )

    async def set_superseded(
        self, *, loser_id: uuid.UUID, winner_id: uuid.UUID
    ) -> None:
        await self.db.execute(
            update(Claim).where(Claim.id == loser_id).values(superseded_by=winner_id)
        )

    async def set_requires_review(
        self, claim_id: uuid.UUID, value: bool = True
    ) -> None:
        await self.db.execute(
            update(Claim)
            .where(Claim.id == claim_id)
            .values(requires_analyst_review=value)
        )

    # ---------------- audit ----------------

    async def write_audit(
        self,
        *,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID | None,
        event: str,
        entity_type: str,
        entity_id: uuid.UUID,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.db.add(
            VerificationAuditLog(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                account_id=account_id,
                event=event,
                entity_type=entity_type,
                entity_id=entity_id,
                data=data or {},
            )
        )
