"""Cross-cutting FastAPI dependencies.

Phase 2:
- get_session            — DB session per request (re-exported from core.db)
- get_current_account    — bearer extraction + JWT verify + account load
- get_active_workspace   — resolves workspace context
- require_capability(c)  — capability-based authorization
- envelope(...)          — canonical successful response wrapper
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.db import get_session
from oryx.core.errors import (
    AuthRequiredError,
    PermissionDeniedError,
    WorkspaceNotFoundError,
)
from oryx.core.models import Account, WorkspaceMember
from oryx.core.security.cookies import SESSION_COOKIE_NAME
from oryx.core.security.jwt import verify_access_token


def get_request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else "unknown"


def envelope(
    data: Any, *, request_id: str, pagination: dict[str, Any] | None = None
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "requestId": request_id,
        "serverTime": datetime.now(UTC).isoformat(),
    }
    if pagination is not None:
        meta["pagination"] = pagination
    return {"data": data, "meta": meta}


# ---------------------------------------------------------------------------
# Auth: bearer extraction and account loading
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CurrentPrincipal:
    account_id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: uuid.UUID


def _read_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _read_token(request: Request) -> str | None:
    """Dual-auth: native sends a bearer header, web relies on the httpOnly
    session cookie. Header wins when both are present so an explicit token
    always overrides an ambient cookie."""
    token = _read_bearer(request)
    if token:
        return token
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    return cookie.strip() if cookie and cookie.strip() else None


def get_principal(request: Request) -> CurrentPrincipal:
    token = _read_token(request)
    if not token:
        raise AuthRequiredError()
    claims = verify_access_token(token)
    return CurrentPrincipal(
        account_id=uuid.UUID(claims.sub),
        workspace_id=uuid.UUID(claims.wsp),
        session_id=uuid.UUID(claims.sid),
    )


def get_principal_optional(request: Request) -> CurrentPrincipal | None:
    token = _read_token(request)
    if not token:
        return None
    try:
        claims = verify_access_token(token)
    except Exception:
        return None
    return CurrentPrincipal(
        account_id=uuid.UUID(claims.sub),
        workspace_id=uuid.UUID(claims.wsp),
        session_id=uuid.UUID(claims.sid),
    )


async def db_session() -> AsyncIterator[AsyncSession]:
    async for s in get_session():
        yield s


async def get_current_account(
    principal: CurrentPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(db_session),
) -> Account:
    result = await session.execute(
        select(Account).where(Account.id == principal.account_id)
    )
    account = result.scalar_one_or_none()
    if account is None or account.deleted_at is not None or account.status != "active":
        raise AuthRequiredError("Account not available")
    return account


async def get_current_account_optional(
    principal: CurrentPrincipal | None = Depends(get_principal_optional),
    session: AsyncSession = Depends(db_session),
) -> Account | None:
    if principal is None:
        return None
    result = await session.execute(
        select(Account).where(Account.id == principal.account_id)
    )
    return result.scalar_one_or_none()


@dataclass(frozen=True)
class ActiveWorkspaceContext:
    workspace_id: uuid.UUID
    role: str


async def get_active_workspace(
    principal: CurrentPrincipal = Depends(get_principal),
    session: AsyncSession = Depends(db_session),
) -> ActiveWorkspaceContext:
    result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == principal.workspace_id,
            WorkspaceMember.account_id == principal.account_id,
            WorkspaceMember.removed_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise WorkspaceNotFoundError()
    return ActiveWorkspaceContext(
        workspace_id=member.workspace_id, role=member.role
    )


# ---------------------------------------------------------------------------
# Capabilities — role-based with wildcard support
# ---------------------------------------------------------------------------

CAPABILITIES: dict[str, list[str]] = {
    "owner": ["*"],
    "admin": [
        "research.*", "settings.*", "integrations.*", "content.*", "activity.*",
        "verification.*",
        # Team/Workspace Rev 2 §6's real trap: a new namespace must be
        # DELIBERATELY added here or admins silently can't invite/manage
        # members even though the routes exist. See
        # tests/unit/test_capability_admin_coverage.py — it fails loudly
        # if a future capability namespace is added without this happening.
        "workspace.*",
    ],
    "editor": [
        "research.write", "research.read", "content.*", "activity.read",
        "verification.read",
    ],
    "reader": ["research.read", "content.read", "activity.read", "verification.read"],
}


def _role_grants(role: str, capability: str) -> bool:
    grants = CAPABILITIES.get(role, [])
    for grant in grants:
        if grant == "*":
            return True
        if grant == capability:
            return True
        if grant.endswith(".*") and capability.startswith(grant[:-2] + "."):
            return True
    return False


def require_capability(capability: str):
    """Dependency factory. Usage:
        @router.post(..., dependencies=[Depends(require_capability('research.write'))])
    """

    async def _check(
        ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    ) -> None:
        if not _role_grants(ws.role, capability):
            raise PermissionDeniedError(
                details={"required": capability, "role": ws.role}
            )

    return _check


async def require_platform_admin(
    account: Account = Depends(get_current_account),
) -> Account:
    """Account-level gate for `intake.platform` surfaces (§17.4).

    Distinct from require_capability: platform admin is a flag on the
    account, never a workspace role — workspace owners must NOT pass.
    """
    if not account.is_platform_admin:
        raise PermissionDeniedError(details={"required": "platform_admin"})
    return account
