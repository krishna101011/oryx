"""Analyst review + conflict resolution service (Wave D).

Every analyst action is APPEND-ONLY: it writes an analyst_reviews row and a
verification_audit_log entry (event='analyst_override'); it never mutates the
original claim or verification_run rows. The only state it changes is
conflict_records (resolution) and claims.superseded_by (the loser pointer) —
both inherent to resolving a conflict, both in ONE transaction with the audit
trail and the outbox event.

Object projections (Wave E): a conflict resolution recomposes the affected
intelligence object via ObjectConflictProjector, which subscribes to the
CONFLICT_RESOLVED event emitted here (OBJECT_UPDATED + OBJECT_REVIEWED). An
object review (approve/reject) flips intelligence_objects.verification_status
inline and emits OBJECT_REVIEWED, in this same transaction.

Note enforcement: the analyst note must be non-empty. The check lives HERE
(HTTP 400), not in the request schema, so it is authoritative and unit-testable
independent of FastAPI validation.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import BadRequestError, NotFoundError
from oryx.services.conflicts.events.constants import CONFLICT_RESOLVED
from oryx.services.conflicts.repository import ConflictRepository
from oryx.services.intelligence.events.constants import OBJECT_REVIEWED
from oryx.services.intelligence.repository import IntelligenceRepository
from oryx.services.queue.outbox import enqueue_event
from oryx.services.review.repository import ReviewRepository

_CONFLICT_OUTCOME = {
    "a_wins": ("resolved_a_wins", "conflict_resolved_a"),
    "b_wins": ("resolved_b_wins", "conflict_resolved_b"),
    "inconclusive": ("resolved_inconclusive", "conflict_inconclusive"),
}

_OBJECT_STATUS = {
    "approved": "analyst_approved",
    "rejected": "analyst_rejected",
    "flagged": None,  # flag is advisory — no status change
}


def _require_note(note: str) -> None:
    if not note or not note.strip():
        raise BadRequestError("An explanatory note is required")


class ReviewService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def resolve_conflict(
        self,
        *,
        conflict_id: uuid.UUID,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        outcome: str,
        note: str,
    ) -> dict[str, Any]:
        _require_note(note)
        status, review_outcome = _CONFLICT_OUTCOME[outcome]

        async with self._sm() as session:
            conflicts = ConflictRepository(session)
            reviews = ReviewRepository(session)

            conflict = await conflicts.get_conflict(
                workspace_id=workspace_id, conflict_id=conflict_id
            )
            if conflict is None:
                raise NotFoundError("Conflict not found")

            winner_id: uuid.UUID | None = None
            loser_id: uuid.UUID | None = None
            if outcome == "a_wins":
                winner_id, loser_id = conflict.claim_a_id, conflict.claim_b_id
            elif outcome == "b_wins":
                winner_id, loser_id = conflict.claim_b_id, conflict.claim_a_id

            await conflicts.resolve_conflict_analyst(
                conflict_id=conflict_id,
                status=status,
                account_id=account_id,
                note=note,
            )
            if winner_id is not None and loser_id is not None:
                await conflicts.set_superseded(loser_id=loser_id, winner_id=winner_id)

            review = await reviews.insert_review(
                account_id=account_id,
                workspace_id=workspace_id,
                entity_type="conflict",
                entity_id=conflict_id,
                outcome=review_outcome,
                note=note,
            )
            await conflicts.write_audit(
                workspace_id=workspace_id,
                account_id=account_id,
                event="analyst_override",
                entity_type="conflict",
                entity_id=conflict_id,
                data={
                    "outcome": outcome,
                    "status": status,
                    "winner_id": str(winner_id) if winner_id else None,
                    "loser_id": str(loser_id) if loser_id else None,
                    "note": note,
                },
            )
            # Object projection (Wave E): ObjectConflictProjector consumes this
            # CONFLICT_RESOLVED event (resolution='analyst') and recomposes the
            # affected object — recalculated score excluding the superseded
            # claim, status restored if no open conflicts remain — emitting
            # OBJECT_UPDATED(changeType='conflict_resolved') + OBJECT_REVIEWED.
            await enqueue_event(
                session,
                name=CONFLICT_RESOLVED,
                payload={
                    "conflictId": str(conflict_id),
                    "claimAId": str(conflict.claim_a_id),
                    "claimBId": str(conflict.claim_b_id),
                    "resolution": "analyst",
                    "winnerId": str(winner_id) if winner_id else None,
                    "loserId": str(loser_id) if loser_id else None,
                    "status": status,
                    "workspaceId": str(workspace_id),
                },
                workspace_id=workspace_id,
                actor_kind="account",
                actor_id=str(account_id),
            )
            await session.commit()

            return {
                "conflictId": str(conflict_id),
                "status": status,
                "resolution": "analyst",
                "winnerId": str(winner_id) if winner_id else None,
                "loserId": str(loser_id) if loser_id else None,
                "reviewId": str(review.id),
            }

    async def review_claim(
        self,
        *,
        claim_id: uuid.UUID,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        outcome: str,
        note: str,
    ) -> dict[str, Any]:
        """Records an analyst judgment on a claim. Creates an analyst_reviews
        row ONLY — the claim row is never mutated."""
        _require_note(note)
        async with self._sm() as session:
            reviews = ReviewRepository(session)
            conflicts = ConflictRepository(session)

            claim = await reviews.get_claim(
                workspace_id=workspace_id, claim_id=claim_id
            )
            if claim is None:
                raise NotFoundError("Claim not found")

            review = await reviews.insert_review(
                account_id=account_id,
                workspace_id=workspace_id,
                entity_type="claim",
                entity_id=claim_id,
                outcome=outcome,
                note=note,
            )
            await conflicts.write_audit(
                workspace_id=workspace_id,
                account_id=account_id,
                event="analyst_override",
                entity_type="claim",
                entity_id=claim_id,
                data={"outcome": outcome, "note": note},
            )
            await session.commit()
            return {
                "claimId": str(claim_id),
                "outcome": outcome,
                "reviewId": str(review.id),
            }

    async def review_object(
        self,
        *,
        object_id: uuid.UUID,
        workspace_id: uuid.UUID,
        account_id: uuid.UUID,
        outcome: str,
        note: str,
    ) -> dict[str, Any]:
        """Records an analyst judgment on an intelligence object. Writes the
        analyst_reviews row + audit entry, flips the object's
        verification_status (approved → analyst_approved, rejected →
        analyst_rejected, flagged → unchanged), and emits OBJECT_REVIEWED —
        all in one transaction."""
        _require_note(note)
        target_status = _OBJECT_STATUS[outcome]
        async with self._sm() as session:
            reviews = ReviewRepository(session)
            conflicts = ConflictRepository(session)
            intel = IntelligenceRepository(session)

            review = await reviews.insert_review(
                account_id=account_id,
                workspace_id=workspace_id,
                entity_type="intelligence_object",
                entity_id=object_id,
                outcome=outcome,
                note=note,
            )
            await conflicts.write_audit(
                workspace_id=workspace_id,
                account_id=account_id,
                event="analyst_override",
                entity_type="intelligence_object",
                entity_id=object_id,
                data={
                    "outcome": outcome,
                    "note": note,
                    "target_status": target_status,
                },
            )

            # Flip status + emit OBJECT_REVIEWED when the object exists. flagged
            # is advisory (target_status None) — the review is still recorded.
            obj = await intel.get_object(
                workspace_id=workspace_id, object_id=object_id
            )
            if obj is not None:
                if target_status is not None:
                    await intel.set_status(object_id=object_id, status=target_status)
                await enqueue_event(
                    session,
                    name=OBJECT_REVIEWED,
                    payload={
                        "objectId": str(object_id),
                        "accountId": str(account_id),
                        "workspaceId": str(workspace_id),
                        "reviewOutcome": outcome,
                    },
                    workspace_id=workspace_id,
                    actor_kind="account",
                    actor_id=str(account_id),
                )
            await session.commit()
            return {
                "objectId": str(object_id),
                "outcome": outcome,
                "reviewId": str(review.id),
            }

    async def get_queue(self, workspace_id: uuid.UUID) -> dict[str, list[Any]]:
        async with self._sm() as session:
            conflicts = ConflictRepository(session)
            pending = await conflicts.list_pending_claims(workspace_id)
            open_conflicts = await conflicts.list_open_conflicts(workspace_id)
            return {"pendingClaims": pending, "openConflicts": open_conflicts}
