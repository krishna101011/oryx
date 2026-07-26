"""Workspaces router — /v1/workspaces/*.

Team/Workspace Rev 2 (docs/TEAM_WORKSPACE_ARCHITECTURE.md) adds: list an
account's workspaces, list/remove members, and the invite mechanism
(create/view/accept/revoke). PATCH /current's rename now has the
capability gate the doc flagged as missing ("currently safe only by
accident").
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.dependencies import (
    ActiveWorkspaceContext,
    CurrentPrincipal,
    db_session,
    envelope,
    get_active_workspace,
    get_current_account,
    get_principal,
    get_request_id,
    require_capability,
)
from oryx.core.errors import (
    InviteEmailMismatchError,
    InviteInvalidError,
    InviteNotFoundError,
    ValidationError,
    WorkspaceNotFoundError,
)
from oryx.core.models import Account, Workspace
from oryx.services.activity.providers.email.factory import get_email_provider
from oryx.services.auth.providers.email.base import EmailMessage
from oryx.services.workspaces.repository import INVITE_TTL, WorkspaceRepository
from oryx.shared.types import (
    AcceptInviteResult,
    ActiveWorkspace,
    CreateInviteRequest,
    WorkspaceActivityEvent,
    WorkspaceActivityListResponse,
    WorkspaceInvitesListResponse,
    WorkspaceMemberSummary,
    WorkspacesListResponse,
)
from oryx.shared.types import Workspace as WorkspaceSchema
from oryx.shared.types import (
    WorkspaceInvite as WorkspaceInviteSchema,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _activity_to_schema(row) -> WorkspaceActivityEvent:
    return WorkspaceActivityEvent(
        id=str(row.id),
        event=row.event,
        actorAccountId=str(row.actor_account_id) if row.actor_account_id else None,
        subjectAccountId=str(row.subject_account_id) if row.subject_account_id else None,
        subjectEmail=row.subject_email,
        role=row.role,
        createdAt=row.created_at,
    )


def _invite_to_schema(invite) -> WorkspaceInviteSchema:
    return WorkspaceInviteSchema(
        id=str(invite.id),
        workspaceId=str(invite.workspace_id),
        invitedEmail=invite.invited_email,
        role=invite.role,
        invitedBy=str(invite.invited_by),
        expiresAt=invite.expires_at,
        acceptedAt=invite.accepted_at,
        revokedAt=invite.revoked_at,
        createdAt=invite.created_at,
    )


@router.get("/current")
async def get_current(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceNotFoundError()
    payload = ActiveWorkspace(
        id=str(workspace.id), name=workspace.name, kind=workspace.kind, role=ws.role
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


class _Rename(WorkspaceSchema):
    pass


@router.patch(
    "/current", dependencies=[Depends(require_capability("workspace.manage"))]
)
async def rename_current(
    body: dict,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    # Phase 2 supports renaming only.
    name = body.get("name")
    if isinstance(name, str) and name.strip():
        await db.execute(
            update(Workspace).where(Workspace.id == ws.workspace_id).values(name=name.strip())
        )
    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise WorkspaceNotFoundError()
    payload = ActiveWorkspace(
        id=str(workspace.id), name=workspace.name, kind=workspace.kind, role=ws.role
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


# ============================================================================
# Team/Workspace Rev 2 §4 — list an account's workspaces
# ============================================================================


@router.get("")
async def list_workspaces(
    request: Request,
    principal: CurrentPrincipal = Depends(get_principal),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    pairs = await repo.list_active_for_account(principal.account_id)
    payload = WorkspacesListResponse(
        workspaces=[
            ActiveWorkspace(id=str(w.id), name=w.name, kind=w.kind, role=role)
            for w, role in pairs
        ]
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


# ============================================================================
# Team/Workspace Rev 2 §3 — member listing + removal
# ============================================================================


@router.get("/members")
async def list_members(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    members = await repo.list_active_members(ws.workspace_id)
    payload = [
        WorkspaceMemberSummary(
            accountId=str(m.account_id), role=m.role, joinedAt=m.joined_at
        ).model_dump(by_alias=True)
        for m in members
    ]
    return envelope(payload, request_id=get_request_id(request))


@router.get("/activity")
async def list_activity(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Team nav promotion wave — the real Team Activity view. Same access
    level as list_members (no workspace.manage gate): any active member can
    see who was invited/joined/removed, matching what the Members list
    already exposes to every role."""
    repo = WorkspaceRepository(db)
    events = await repo.list_activity(ws.workspace_id)
    payload = WorkspaceActivityListResponse(
        events=[_activity_to_schema(e) for e in events]
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.delete(
    "/members/{account_id}",
    dependencies=[Depends(require_capability("workspace.manage"))],
)
async def remove_member(
    account_id: str,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    target_id = uuid.UUID(account_id)
    repo = WorkspaceRepository(db)
    # Protect the sole owner: ownership is singular per workspace
    # (Workspace.owner_account_id) and isn't reassigned by this endpoint.
    members = await repo.list_active_members(ws.workspace_id)
    target = next((m for m in members if m.account_id == target_id), None)
    if target is None:
        raise WorkspaceNotFoundError("Not an active member of this workspace")
    if target.role == "owner":
        raise ValidationError("The workspace owner cannot be removed")
    removed = await repo.remove_member(workspace_id=ws.workspace_id, account_id=target_id)
    if removed is None:
        raise WorkspaceNotFoundError("Not an active member of this workspace")
    await repo.record_activity(
        workspace_id=ws.workspace_id,
        event="member_removed",
        actor_account_id=account.id,
        subject_account_id=target_id,
        role=target.role,
    )
    return envelope({"removed": True}, request_id=get_request_id(request))


# ============================================================================
# Team/Workspace Rev 2 §3 — invite mechanism
# ============================================================================


@router.post(
    "/invites", dependencies=[Depends(require_capability("workspace.manage"))]
)
async def create_invite(
    body: CreateInviteRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)

    existing_member = await repo.get_active_member_by_email(
        workspace_id=ws.workspace_id, email=body.email
    )
    if existing_member is not None:
        raise ValidationError("This email already belongs to the workspace")

    pending = await repo.get_pending_email_invite(
        workspace_id=ws.workspace_id, invited_email=body.email
    )
    if pending is not None:
        raise ValidationError("An invite is already pending for this email")

    invite, raw_token = await repo.create_invite(
        workspace_id=ws.workspace_id,
        invited_email=body.email,
        role=body.role,
        invited_by=account.id,
    )
    await repo.record_activity(
        workspace_id=ws.workspace_id,
        event="member_invited",
        actor_account_id=account.id,
        subject_email=body.email,
        role=body.role,
    )

    result = await db.execute(select(Workspace).where(Workspace.id == ws.workspace_id))
    workspace = result.scalar_one()
    await get_email_provider().send(
        EmailMessage(
            to=body.email,
            template="invite",
            variables={
                "workspace_name": workspace.name,
                "inviter_display_name": account.email,
                "role": body.role,
                "invite_token": raw_token,
                "expires_days": str(INVITE_TTL.days),
            },
        )
    )
    return envelope(
        _invite_to_schema(invite).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.get(
    "/invites", dependencies=[Depends(require_capability("workspace.manage"))]
)
async def list_invites(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Members-screen gap found while building the UI (not in the frozen
    Rev 2 doc's endpoint list): create/view/accept/revoke existed, but
    nothing let a workspace list its own pending invites. Same capability
    gate as create_invite; never accepted, never revoked (see
    WorkspaceRepository.list_pending_invites for why expired ones stay in
    this list rather than being silently filtered out)."""
    repo = WorkspaceRepository(db)
    invites = await repo.list_pending_invites(ws.workspace_id)
    payload = WorkspaceInvitesListResponse(
        invites=[_invite_to_schema(i) for i in invites]
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.get("/invites/{token}")
async def view_invite(
    token: str,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Lightly authenticated per the doc: any signed-in account may preview
    an invite by token (they aren't a member of the target workspace yet, so
    get_active_workspace can't gate this). A found-but-resolved invite
    (expired/revoked/accepted) still returns 200 — the client renders the
    real state from its fields; only a genuinely unknown token 404s."""
    repo = WorkspaceRepository(db)
    invite = await repo.get_invite_by_token(token)
    if invite is None:
        raise InviteNotFoundError()
    return envelope(
        _invite_to_schema(invite).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str,
    request: Request,
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    invite = await repo.get_invite_by_token(token)
    if invite is None:
        raise InviteNotFoundError()
    if invite.invited_email.lower() != account.email.lower():
        raise InviteEmailMismatchError()

    accepted = await repo.accept_invite(invite.id)
    if not accepted:
        # Either the loser of a concurrent accept race, or genuinely expired/
        # revoked/already-accepted by the time this ran — same honest bucket.
        raise InviteInvalidError()

    joined_at = await repo.join_workspace(
        workspace_id=invite.workspace_id,
        account_id=account.id,
        role=invite.role,
        invited_by=invite.invited_by,
    )
    await repo.record_activity(
        workspace_id=invite.workspace_id,
        event="member_joined",
        actor_account_id=account.id,
        subject_account_id=account.id,
        role=invite.role,
    )
    payload = AcceptInviteResult(
        workspaceId=str(invite.workspace_id), role=invite.role, joinedAt=joined_at
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.post(
    "/invites/{invite_id}/revoke",
    dependencies=[Depends(require_capability("workspace.manage"))],
)
async def revoke_invite(
    invite_id: str,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    invite = await repo.get_invite_by_id(uuid.UUID(invite_id))
    # Don't leak whether an invite ID from another workspace exists.
    if invite is None or invite.workspace_id != ws.workspace_id:
        raise InviteNotFoundError()
    revoked = await repo.revoke_invite(invite.id)
    if not revoked:
        raise InviteInvalidError()
    return envelope({"revoked": True}, request_id=get_request_id(request))
