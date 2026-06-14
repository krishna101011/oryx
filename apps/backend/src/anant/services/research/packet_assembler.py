"""Packet readiness gate (Wave E).

The gate is enforced HERE (service layer), not just the mobile UI: a packet
cannot move to 'ready' while any constituent object is rejected, or contested
without an explicit acknowledgement. The router turns a non-ready result into
HTTP 409.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.errors import NotFoundError
from anant.services.research.models import (
    ObjectReadinessInput,
    ReadinessResult,
    evaluate_readiness,
)
from anant.services.research.repository import ResearchRepository


class PacketAssembler:
    async def check_readiness(
        self,
        *,
        packet_id: uuid.UUID,
        workspace_id: uuid.UUID,
        session: AsyncSession,
    ) -> ReadinessResult:
        repo = ResearchRepository(session)
        packet = await repo.get_packet(
            workspace_id=workspace_id, packet_id=packet_id
        )
        if packet is None:
            raise NotFoundError("Research packet not found")
        objects = await repo.get_objects_by_ids(
            workspace_id=workspace_id, ids=list(packet.intelligence_object_ids or [])
        )
        inputs = [
            ObjectReadinessInput(
                id=str(o.id),
                headline=o.headline,
                verification_status=o.verification_status,
            )
            for o in objects
        ]
        acknowledged = {str(x) for x in (packet.conflict_acknowledged_ids or [])}
        return evaluate_readiness(inputs, acknowledged)
