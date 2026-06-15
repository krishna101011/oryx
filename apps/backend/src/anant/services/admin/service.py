"""Admin re-run orchestration (Wave F). Platform-admin only.

Operational tools for after a code/version change: re-extract claims from intake
items, re-verify claims, and re-score existing runs + objects. Re-extraction and
re-verification work by enqueuing the SAME domain events the live pipeline uses
(no bypass) — the existing handlers do the work. Re-scoring updates in place
because a score is a formula output, not a world-fact (ADR-032).
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from anant.core.models import (
    Claim,
    IntakeItem,
    IntelligenceObject,
    VerificationRun,
    WorkspaceAIBudget,
)
from anant.core.scoring_version import CURRENT_SCORING_VERSION
from anant.services.claims.repository import DEFAULT_BUDGET_LIMIT
from anant.services.evidence.events.constants import EVIDENCE_COLLECTED
from anant.services.intake.events_constants import INTAKE_ITEM_RECEIVED
from anant.services.intelligence.composer import ObjectComposer
from anant.services.intelligence.events.constants import OBJECT_UPDATED
from anant.services.intelligence.repository import (
    STICKY_STATUSES,
    IntelligenceRepository,
)
from anant.services.queue.outbox import enqueue_event
from anant.services.verification.engine import ENGINE_VERSION
from anant.services.verification.repository import VerificationRepository
from anant.services.verification.scorer import ConfidenceScorer


class AdminVerificationService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker
        self._scorer = ConfidenceScorer()
        self._composer = ObjectComposer()

    async def reextract(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_item_ids: list[uuid.UUID] | None,
        dry_run: bool,
        account_id: uuid.UUID,
    ) -> int:
        async with self._sm() as session:
            stmt = select(IntakeItem).where(IntakeItem.workspace_id == workspace_id)
            if intake_item_ids is not None:
                stmt = stmt.where(IntakeItem.id.in_(intake_item_ids))
            items = list((await session.execute(stmt)).scalars().all())

            if dry_run:
                return len(items)

            for item in items:
                await enqueue_event(
                    session,
                    name=INTAKE_ITEM_RECEIVED,
                    payload={
                        "intakeItemId": str(item.id),
                        "workspaceId": str(workspace_id),
                        "intakeSourceId": str(item.intake_source_id),
                        "providerName": item.provider_name,
                        "receivedAt": item.received_at.isoformat(),
                        "fingerprint": item.fingerprint,
                        "externalId": item.external_id,
                    },
                    workspace_id=workspace_id,
                    actor_kind="account",
                    actor_id=str(account_id),
                )
            await session.commit()
            return len(items)

    async def reverify(
        self,
        *,
        workspace_id: uuid.UUID,
        claim_ids: list[uuid.UUID],
        reason: str,
        account_id: uuid.UUID,
    ) -> int:
        queued = 0
        async with self._sm() as session:
            repo = VerificationRepository(session)
            for claim_id in claim_ids:
                claim = await repo.get_claim(
                    workspace_id=workspace_id, claim_id=claim_id
                )
                if claim is None:
                    continue
                session.add(
                    VerificationRun(
                        id=uuid.uuid4(),
                        claim_id=claim_id,
                        status="pending",
                        engine_version=ENGINE_VERSION,
                        scoring_version=CURRENT_SCORING_VERSION,
                        started_at=datetime.now(UTC),
                    )
                )
                await repo.write_audit(
                    workspace_id=workspace_id,
                    account_id=account_id,
                    event="reverify_requested",
                    entity_type="claim",
                    entity_id=claim_id,
                    data={"reason": reason},
                )
                await enqueue_event(
                    session,
                    name=EVIDENCE_COLLECTED,
                    payload={
                        "claimId": str(claim_id),
                        "workspaceId": str(workspace_id),
                    },
                    workspace_id=workspace_id,
                    actor_kind="account",
                    actor_id=str(account_id),
                )
                queued += 1
            await session.commit()
        return queued

    async def rescore(self, *, workspace_id: uuid.UUID) -> tuple[int, int]:
        now = datetime.now(UTC)
        updated_runs = 0
        # ---- verification runs ----
        async with self._sm() as session:
            repo = VerificationRepository(session)
            runs = list(
                (
                    await session.execute(
                        select(VerificationRun)
                        .join(Claim, Claim.id == VerificationRun.claim_id)
                        .where(
                            Claim.workspace_id == workspace_id,
                            VerificationRun.status == "complete",
                        )
                    )
                ).scalars().all()
            )
            for run in runs:
                claim = await repo.get_claim(
                    workspace_id=workspace_id, claim_id=run.claim_id
                )
                if claim is None:
                    continue
                item = await repo.get_intake_item(claim.intake_item_id)
                if item is None:
                    continue
                accuracy = await repo.get_accuracy(
                    workspace_id=workspace_id, source_id=item.intake_source_id
                )
                links = await repo.get_evidence_links(run.claim_id)
                scoring = self._scorer.score(
                    epistemic_type=claim.epistemic_type,
                    accuracy_rate=accuracy,
                    links=links,
                    received_at=item.received_at,
                    object_text=claim.object,
                    now=now,
                )
                run.confidence_score = scoring.confidence_score
                run.scoring_version = CURRENT_SCORING_VERSION
                updated_runs += 1
            await session.commit()

        # ---- intelligence objects ----
        updated_objects = 0
        async with self._sm() as session:
            intel = IntelligenceRepository(session)
            objects = list(
                (
                    await session.execute(
                        select(IntelligenceObject).where(
                            IntelligenceObject.workspace_id == workspace_id
                        )
                    )
                ).scalars().all()
            )
            for obj in objects:
                result = await self._composer.compose(
                    intake_item_id=obj.intake_item_id,
                    workspace_id=workspace_id,
                    session=session,
                )
                status = (
                    obj.verification_status
                    if obj.verification_status in STICKY_STATUSES
                    else result.verification_status
                )
                await intel.apply_composition(
                    object_id=obj.id, result=result, status=status
                )
                await enqueue_event(
                    session,
                    name=OBJECT_UPDATED,
                    payload={
                        "objectId": str(obj.id),
                        "workspaceId": str(workspace_id),
                        "changeType": "score_update",
                    },
                    workspace_id=workspace_id,
                )
                updated_objects += 1
            await session.commit()
        return updated_runs, updated_objects

    async def budget(self, *, workspace_id: uuid.UUID) -> dict[str, Any]:
        async with self._sm() as session:
            today = date.today()
            row = (
                await session.execute(
                    select(
                        WorkspaceAIBudget.tokens_used, WorkspaceAIBudget.budget_limit
                    ).where(
                        WorkspaceAIBudget.workspace_id == workspace_id,
                        WorkspaceAIBudget.budget_date == today,
                    )
                )
            ).one_or_none()
            if row is None:
                tokens_used, budget_limit = 0, DEFAULT_BUDGET_LIMIT
            else:
                tokens_used, budget_limit = int(row[0]), int(row[1])
            utilization = (tokens_used / budget_limit) if budget_limit else 0.0
            return {
                "workspace_id": str(workspace_id),
                "tokens_used": tokens_used,
                "budget_limit": budget_limit,
                "utilization": utilization,
            }
