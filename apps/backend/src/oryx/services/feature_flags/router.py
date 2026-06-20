"""Feature flags router.

- /v1/feature-flags        — resolved flag map for the principal
- /v1/admin/feature-flags/overrides (POST) — platform-admin only
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    db_session,
    envelope,
    get_active_workspace,
    get_current_account,
    get_request_id,
)
from oryx.core.errors import PermissionDeniedError
from oryx.core.models import Account, FeatureFlagOverride
from oryx.services.feature_flags.resolver import resolve_flags

router = APIRouter(tags=["feature_flags"])


@router.get("/feature-flags")
async def get_flags(
    request: Request,
    account: Account = Depends(get_current_account),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    flags = await resolve_flags(
        db, account_id=account.id, workspace_id=ws.workspace_id
    )
    return envelope(flags, request_id=get_request_id(request))


class _OverrideBody(BaseModel):
    flagKey: str
    scope: str  # 'account' | 'workspace'
    scopeId: uuid.UUID
    enabled: bool
    expiresAt: datetime | None = None


@router.post("/admin/feature-flags/overrides")
async def set_override(
    body: _OverrideBody,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    if not account.is_platform_admin:
        raise PermissionDeniedError()
    stmt = pg_insert(FeatureFlagOverride).values(
        flag_key=body.flagKey,
        scope=body.scope,
        scope_id=body.scopeId,
        enabled=body.enabled,
        expires_at=body.expiresAt,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["flag_key", "scope", "scope_id"],
        set_={"enabled": stmt.excluded.enabled, "expires_at": stmt.excluded.expires_at},
    )
    await db.execute(stmt)
    return envelope({"ok": True}, request_id=get_request_id(request))
