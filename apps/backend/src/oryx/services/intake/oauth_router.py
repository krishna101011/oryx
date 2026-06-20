"""Gmail OAuth router — start, callback, disconnect.

Distinct from the main intake router because OAuth is its own subsystem:
  - start    : creates an intake_sources row in 'auth_required' status,
               returns a Google consent URL
  - callback : exchanges the code, stores encrypted tokens, marks the
               source 'healthy', captures the initial historyId
  - disconnect : revokes upstream + deletes credentials + marks 'disabled'
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    CurrentPrincipal,
    db_session,
    envelope,
    get_active_workspace,
    get_principal,
    get_request_id,
    require_capability,
)
from oryx.core.errors import NotFoundError, ValidationError
from oryx.core.logging import get_logger
from oryx.core.models import IntakeAuditLog, IntakeSource
from oryx.services.intake.credentials import IntakeCredentialsRepository
from oryx.services.intake.providers.gmail import auth as gmail_auth
from oryx.services.intake.providers.gmail import client as gmail_client
from oryx.services.intake.providers.gmail.config_schema import GmailSourceConfig

logger = get_logger(__name__)

router = APIRouter(prefix="/intake/oauth/gmail", tags=["intake-oauth"])


class _StartBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    config: dict[str, Any] = {}


def _gmail_settings() -> tuple[str, str, str]:
    s = get_settings()
    client_id = getattr(s, "gmail_client_id", None)
    client_secret = getattr(s, "gmail_client_secret", None)
    redirect_uri = getattr(
        s,
        "gmail_redirect_uri",
        f"http://localhost:8000{s.api_prefix}/intake/oauth/gmail/callback",
    )
    if not client_id or not client_secret:
        raise ValidationError(
            details={"reason": "gmail_oauth_not_configured"}
        )
    return client_id, client_secret, redirect_uri


@router.post(
    "/start",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def start(
    body: _StartBody,
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Validate config before we mint a source row.
    try:
        GmailSourceConfig.model_validate(body.config)
    except Exception as e:
        raise ValidationError(
            details={"reason": "invalid_gmail_config", "message": str(e)}
        ) from e
    client_id, _, redirect_uri = _gmail_settings()

    src = IntakeSource(
        id=uuid.uuid4(),
        workspace_id=ws.workspace_id,
        kind="gmail",
        name=body.name,
        enabled=True,
        config=body.config,
        origin_kind="catalog",
        origin_catalog_key="gmail",
        status="auth_required",
    )
    db.add(src)
    await db.flush()

    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=src.id,
            event="oauth_started",
            data={},
        )
    )

    state = gmail_auth.encode_state(
        workspace_id=ws.workspace_id,
        account_id=principal.account_id,
        intake_source_id=src.id,
    )
    auth_url = gmail_auth.build_auth_url(
        client_id=client_id, redirect_uri=redirect_uri, state=state
    )
    return envelope(
        {"intakeSourceId": str(src.id), "authUrl": auth_url},
        request_id=get_request_id(request),
    )


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Public callback (no bearer required — relies on signed state JWT)."""
    claims = gmail_auth.decode_state(state)
    client_id, client_secret, redirect_uri = _gmail_settings()

    bundle = await gmail_auth.exchange_code(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    # Confirm the source still exists in the workspace and is the one we minted.
    result = await db.execute(
        select(IntakeSource).where(
            IntakeSource.id == claims.intake_source_id,
            IntakeSource.workspace_id == claims.workspace_id,
            IntakeSource.deleted_at.is_(None),
        )
    )
    src = result.scalar_one_or_none()
    if src is None:
        raise NotFoundError("Source no longer exists")

    creds = IntakeCredentialsRepository(db)
    await creds.store(
        intake_source_id=src.id,
        workspace_id=claims.workspace_id,
        token=bundle.access_token.encode("utf-8"),
        refresh_token=bundle.refresh_token.encode("utf-8") if bundle.refresh_token else None,
        token_expires_at=datetime.now(UTC).replace(microsecond=0),
    )

    # Verify the token + capture the initial historyId for the cursor seed.
    try:
        profile = await gmail_client.get_profile(access_token=bundle.access_token)
        history_id = str(profile.get("historyId")) if profile.get("historyId") else None
    except Exception:
        history_id = None
    src.cursor = {"history_id": history_id, "bootstrap_complete": False}
    src.status = "healthy"
    src.updated_at = datetime.now(UTC)
    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=claims.workspace_id,
            intake_source_id=src.id,
            event="oauth_connected",
            data={"scope": bundle.scope},
        )
    )
    await db.flush()
    return envelope(
        {"intakeSourceId": str(src.id), "connected": True},
        request_id=get_request_id(request),
    )


@router.post(
    "/disconnect/{source_id}",
    dependencies=[Depends(require_capability("intake.write"))],
)
async def disconnect(
    source_id: uuid.UUID,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(
        select(IntakeSource).where(
            IntakeSource.id == source_id,
            IntakeSource.workspace_id == ws.workspace_id,
            IntakeSource.deleted_at.is_(None),
        )
    )
    src = result.scalar_one_or_none()
    if src is None:
        raise NotFoundError("Source not found")

    creds_repo = IntakeCredentialsRepository(db)
    pair = await creds_repo.load(
        intake_source_id=src.id, workspace_id=ws.workspace_id
    )
    if pair is not None and pair.refresh_token:
        # Best-effort upstream revoke.
        try:
            await gmail_auth.revoke_token(pair.refresh_token.decode("utf-8"))
        except Exception as e:
            # Best-effort by contract (ADR-023); local deletion proceeds.
            logger.warning(
                "gmail.revoke_failed",
                extra={"intake_source_id": str(src.id), "error_class": type(e).__name__},
            )
    await creds_repo.delete(intake_source_id=src.id)
    src.status = "disabled"
    src.enabled = False
    src.updated_at = datetime.now(UTC)
    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=ws.workspace_id,
            intake_source_id=src.id,
            event="oauth_disconnected",
            data={},
        )
    )
    await db.flush()
    return envelope({"ok": True}, request_id=get_request_id(request))
