"""Evidence repository — DB operations only, no business rules."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import Claim, ClaimEvidenceLink, Evidence, Workspace


class EvidenceRepository:
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

    # ---------------- evidence ----------------

    async def find_evidence_for_item(
        self, *, workspace_id: uuid.UUID, intake_item_id: uuid.UUID
    ) -> Evidence | None:
        """Dedup lookup: one evidence row per (workspace, intake item)."""
        result = await self.db.execute(
            select(Evidence)
            .where(
                Evidence.workspace_id == workspace_id,
                Evidence.intake_item_id == intake_item_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def insert_evidence(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_item_id: uuid.UUID,
        evidence_type: str,
        text: str,
    ) -> Evidence:
        row = Evidence(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            intake_item_id=intake_item_id,
            evidence_type=evidence_type,
            text=text,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_evidence(
        self, *, workspace_id: uuid.UUID, evidence_id: uuid.UUID
    ) -> Evidence | None:
        result = await self.db.execute(
            select(Evidence).where(
                Evidence.id == evidence_id, Evidence.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    # ---------------- links ----------------

    async def get_links_for_claim(self, claim_id: uuid.UUID) -> list[ClaimEvidenceLink]:
        result = await self.db.execute(
            select(ClaimEvidenceLink).where(ClaimEvidenceLink.claim_id == claim_id)
        )
        return list(result.scalars().all())

    async def insert_link(
        self,
        *,
        claim_id: uuid.UUID,
        evidence_id: uuid.UUID,
        relationship: str,
        strength: float,
        linker_version: int,
    ) -> bool:
        """Returns False when the (claim, evidence) link already existed."""
        stmt = (
            pg_insert(ClaimEvidenceLink)
            .values(
                claim_id=claim_id,
                evidence_id=evidence_id,
                relationship=relationship,
                strength=strength,
                linker_version=linker_version,
            )
            .on_conflict_do_nothing(index_elements=["claim_id", "evidence_id"])
            .returning(ClaimEvidenceLink.claim_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_evidence_with_links(
        self, *, workspace_id: uuid.UUID, claim_id: uuid.UUID
    ) -> list[tuple[Evidence, ClaimEvidenceLink]]:
        result = await self.db.execute(
            select(Evidence, ClaimEvidenceLink)
            .join(ClaimEvidenceLink, ClaimEvidenceLink.evidence_id == Evidence.id)
            .where(
                ClaimEvidenceLink.claim_id == claim_id,
                Evidence.workspace_id == workspace_id,
            )
            .order_by(ClaimEvidenceLink.strength.desc())
        )
        return [(row[0], row[1]) for row in result.all()]
