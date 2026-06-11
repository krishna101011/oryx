"""Sessions router — list and revoke active sessions."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.dependencies import (
    CurrentPrincipal,
    db_session,
    envelope,
    get_principal,
    get_request_id,
)
from anant.services.auth.repository import AuthRepository
from anant.shared.types import Session as SessionSchema

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = AuthRepository(db)
    rows = await repo.list_active_sessions(principal.account_id)
    payload = [
        SessionSchema(
            id=str(r.id),
            deviceLabel=r.device_label,
            devicePlatform=r.device_platform,
            createdAt=r.created_at,
            lastUsedAt=r.last_used_at,
            expiresAt=r.expires_at,
            current=(r.id == principal.session_id),
        ).model_dump(by_alias=True)
        for r in rows
    ]
    return envelope(payload, request_id=get_request_id(request))


@router.delete("/{session_id}")
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = AuthRepository(db)
    sessions = await repo.list_active_sessions(principal.account_id)
    if not any(s.id == session_id for s in sessions):
        # Either someone else's session or already revoked; return same shape (don't leak).
        return envelope({"ok": True}, request_id=get_request_id(request))
    await repo.revoke_session(session_id, reason="user_revoke")
    return envelope({"ok": True}, request_id=get_request_id(request))
