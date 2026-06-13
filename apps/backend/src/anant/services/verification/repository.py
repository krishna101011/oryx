"""Verification repository — DB operations only, no business rules."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import (
    Claim,
    IntakeItem,
    SourceCredibilityRecord,
    VerificationAuditLog,
    VerificationRun,
    Workspace,
)
from anant.services.verification.models import EvidenceLinkInput

DEFAULT_ACCURACY = 0.5


class VerificationRepository:
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

    async def get_evidence_links(self, claim_id: uuid.UUID) -> list[EvidenceLinkInput]:
        from anant.core.models import ClaimEvidenceLink, Evidence

        result = await self.db.execute(
            select(
                ClaimEvidenceLink.relationship,
                ClaimEvidenceLink.strength,
                Evidence.evidence_type,
            )
            .join(Evidence, Evidence.id == ClaimEvidenceLink.evidence_id)
            .where(ClaimEvidenceLink.claim_id == claim_id)
        )
        return [
            EvidenceLinkInput(
                relationship=row.relationship,
                strength=row.strength,
                evidence_type=row.evidence_type,
            )
            for row in result.all()
        ]

    # ---------------- verification runs ----------------

    async def latest_complete_run(
        self,
        *,
        claim_id: uuid.UUID,
        engine_version: int,
        scoring_version: int,
    ) -> VerificationRun | None:
        result = await self.db.execute(
            select(VerificationRun)
            .where(
                VerificationRun.claim_id == claim_id,
                VerificationRun.status == "complete",
                VerificationRun.engine_version == engine_version,
                VerificationRun.scoring_version == scoring_version,
            )
            .order_by(VerificationRun.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def insert_run(self, run: VerificationRun) -> VerificationRun:
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_run(
        self, *, workspace_id: uuid.UUID, run_id: uuid.UUID
    ) -> VerificationRun | None:
        """Workspace-scoped via the claim join."""
        result = await self.db.execute(
            select(VerificationRun)
            .join(Claim, Claim.id == VerificationRun.claim_id)
            .where(
                VerificationRun.id == run_id, Claim.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def list_runs_for_claim(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> list[VerificationRun]:
        result = await self.db.execute(
            select(VerificationRun)
            .join(Claim, Claim.id == VerificationRun.claim_id)
            .where(
                VerificationRun.claim_id == claim_id,
                Claim.workspace_id == workspace_id,
            )
            .order_by(VerificationRun.started_at.desc())
        )
        return list(result.scalars().all())

    # ---------------- source credibility ----------------

    async def get_accuracy(
        self, *, workspace_id: uuid.UUID, source_id: uuid.UUID
    ) -> float:
        """The credibility as it stands now; neutral prior when no record."""
        result = await self.db.execute(
            select(SourceCredibilityRecord.accuracy_rate).where(
                SourceCredibilityRecord.workspace_id == workspace_id,
                SourceCredibilityRecord.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else DEFAULT_ACCURACY

    async def get_credibility(
        self, *, workspace_id: uuid.UUID, source_id: uuid.UUID
    ) -> SourceCredibilityRecord | None:
        result = await self.db.execute(
            select(SourceCredibilityRecord).where(
                SourceCredibilityRecord.workspace_id == workspace_id,
                SourceCredibilityRecord.source_id == source_id,
            )
        )
        return result.scalar_one_or_none()

    async def apply_credibility_outcome(
        self,
        *,
        workspace_id: uuid.UUID,
        source_id: uuid.UUID,
        outcome: str,
        new_accuracy: float,
    ) -> None:
        """Upsert: set the recomputed accuracy and increment outcome counters."""
        now = datetime.now(UTC)
        verified = 1 if outcome == "verified" else 0
        contested = 1 if outcome == "contested" else 0
        stmt = (
            pg_insert(SourceCredibilityRecord)
            .values(
                workspace_id=workspace_id,
                source_id=source_id,
                accuracy_rate=new_accuracy,
                total_claim_count=1,
                verified_claim_count=verified,
                contested_claim_count=contested,
                last_evaluated_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["workspace_id", "source_id"],
                set_={
                    "accuracy_rate": new_accuracy,
                    "total_claim_count": SourceCredibilityRecord.total_claim_count + 1,
                    "verified_claim_count": SourceCredibilityRecord.verified_claim_count
                    + verified,
                    "contested_claim_count": SourceCredibilityRecord.contested_claim_count
                    + contested,
                    "last_evaluated_at": now,
                    "updated_at": now,
                },
            )
        )
        await self.db.execute(stmt)

    async def list_credibility(
        self, workspace_id: uuid.UUID
    ) -> list[SourceCredibilityRecord]:
        result = await self.db.execute(
            select(SourceCredibilityRecord)
            .where(SourceCredibilityRecord.workspace_id == workspace_id)
            .order_by(SourceCredibilityRecord.accuracy_rate.desc())
        )
        return list(result.scalars().all())

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
