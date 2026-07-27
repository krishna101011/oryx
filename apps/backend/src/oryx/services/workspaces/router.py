"""Workspaces router — /v1/workspaces/*.

Team/Workspace Rev 2 (docs/TEAM_WORKSPACE_ARCHITECTURE.md) adds: list an
account's workspaces, list/remove members, and the invite mechanism
(create/view/accept/revoke). PATCH /current's rename now has the
capability gate the doc flagged as missing ("currently safe only by
accident").
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
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
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    WorkspaceNotFoundError,
)
from oryx.core.models import Account, Workspace
from oryx.core.pagination import decode_cursor, encode_cursor
from oryx.services.activity.providers.email.factory import get_email_provider
from oryx.services.auth.providers.email.base import EmailMessage
from oryx.services.queue.outbox import enqueue_event
from oryx.services.workspaces.events.constants import CHAT_MESSAGE_SENT
from oryx.services.workspaces.repository import INVITE_TTL, WorkspaceRepository
from oryx.shared.types import (
    AcceptInviteResult,
    ActiveWorkspace,
    ChangeMemberRoleRequest,
    ChatReadMarker,
    CreateInviteRequest,
    EditChatMessageRequest,
    MarkChatReadRequest,
    SendChatMessageRequest,
    WorkspaceActivityEvent,
    WorkspaceActivityListResponse,
    WorkspaceInvitesListResponse,
    WorkspaceMemberSummary,
    WorkspacesListResponse,
)
from oryx.shared.types import ChatMessage as ChatMessageSchema
from oryx.shared.types import Workspace as WorkspaceSchema
from oryx.shared.types import (
    WorkspaceInvite as WorkspaceInviteSchema,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

DEFAULT_MESSAGE_LIMIT = 50
MAX_MESSAGE_LIMIT = 200
MAX_MESSAGE_BODY_LENGTH = 4000


def _activity_to_schema(row) -> WorkspaceActivityEvent:
    return WorkspaceActivityEvent(
        id=str(row.id),
        event=row.event,
        actorAccountId=str(row.actor_account_id) if row.actor_account_id else None,
        subjectAccountId=str(row.subject_account_id) if row.subject_account_id else None,
        subjectEmail=row.subject_email,
        role=row.role,
        previousRole=row.previous_role,
        createdAt=row.created_at,
    )


def _message_to_schema(row) -> ChatMessageSchema:
    return ChatMessageSchema(
        id=str(row.id),
        workspaceId=str(row.workspace_id),
        senderAccountId=str(row.sender_account_id),
        # Soft-delete redacts content at the API layer only — the real body
        # stays in the row (deleted_at set), clients just stop seeing it.
        body=row.body if row.deleted_at is None else None,
        createdAt=row.created_at,
        editedAt=row.edited_at,
        deletedAt=row.deleted_at,
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


# ============================================================================
# Team Chat foundation wave — a single workspace-wide channel (§ recon:
# WorkspaceAuditLog was NOT extended for this; see its own docstring for why).
# Same access level as list_members/list_activity: any active member (any
# role) can read and post — no workspace.manage gate. Edit/delete are
# additionally restricted to the message's own sender, checked here (not in
# the repository), matching change_member_role's "guard in the router"
# convention.
# ============================================================================


@router.post("/messages")
async def send_message(
    body: SendChatMessageRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    text = body.body.strip()
    if not text:
        raise ValidationError("Message body cannot be empty")
    if len(text) > MAX_MESSAGE_BODY_LENGTH:
        raise ValidationError(
            "Message body too long",
            details={"maxLength": MAX_MESSAGE_BODY_LENGTH},
        )
    repo = WorkspaceRepository(db)
    row = await repo.send_message(
        workspace_id=ws.workspace_id, sender_account_id=account.id, body=text
    )
    await enqueue_event(
        db,
        name=CHAT_MESSAGE_SENT,
        payload={
            "messageId": str(row.id),
            "senderAccountId": str(account.id),
        },
        workspace_id=ws.workspace_id,
        actor_kind="account",
        actor_id=str(account.id),
    )
    return envelope(
        _message_to_schema(row).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.get("/messages")
async def list_messages(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    db: AsyncSession = Depends(db_session),
    since: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_MESSAGE_LIMIT, ge=1, le=MAX_MESSAGE_LIMIT),
) -> dict:
    """`since` omitted returns the latest page of history; `since` set to a
    prior response's nextCursor returns only messages strictly after it — the
    real "don't refetch the whole history on every poll" behavior (recon
    flagged WorkspaceAuditLog's unpaginated "latest 50" as unfit for this;
    this is deliberately NOT that shape)."""
    repo = WorkspaceRepository(db)
    if since:
        decoded = decode_cursor(since)
        after_created_at = datetime.fromisoformat(decoded["createdAt"])
        after_id = uuid.UUID(decoded["id"])
        rows = await repo.list_messages_after(
            workspace_id=ws.workspace_id,
            after_created_at=after_created_at,
            after_id=after_id,
            limit=limit,
        )
    else:
        rows = await repo.list_latest_messages(workspace_id=ws.workspace_id, limit=limit)

    if rows:
        last = rows[-1]
        next_cursor = encode_cursor({"createdAt": last.created_at.isoformat(), "id": str(last.id)})
    else:
        # Nothing new since the caller's cursor — hand the same cursor back
        # so the next poll compares against the same point, not "no cursor"
        # (which would re-fetch the latest page instead of waiting for new).
        next_cursor = since

    return envelope(
        [_message_to_schema(r).model_dump(by_alias=True) for r in rows],
        request_id=get_request_id(request),
        pagination={"nextCursor": next_cursor, "prevCursor": None},
    )


async def _get_own_message_or_error(repo: WorkspaceRepository, *, message_id: uuid.UUID, ws: ActiveWorkspaceContext, account: Account):
    message = await repo.get_message(message_id)
    if (
        message is None
        or message.workspace_id != ws.workspace_id
        or message.deleted_at is not None
    ):
        raise NotFoundError("Message not found")
    if message.sender_account_id != account.id:
        raise PermissionDeniedError(details={"reason": "not_sender"})
    return message


@router.patch("/messages/{message_id}")
async def edit_message(
    message_id: str,
    body: EditChatMessageRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    text = body.body.strip()
    if not text:
        raise ValidationError("Message body cannot be empty")
    if len(text) > MAX_MESSAGE_BODY_LENGTH:
        raise ValidationError(
            "Message body too long",
            details={"maxLength": MAX_MESSAGE_BODY_LENGTH},
        )
    repo = WorkspaceRepository(db)
    target = await _get_own_message_or_error(
        repo, message_id=uuid.UUID(message_id), ws=ws, account=account
    )
    updated = await repo.edit_message(message_id=target.id, body=text)
    if updated is None:
        raise NotFoundError("Message not found")
    return envelope(
        _message_to_schema(updated).model_dump(by_alias=True),
        request_id=get_request_id(request),
    )


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    target = await _get_own_message_or_error(
        repo, message_id=uuid.UUID(message_id), ws=ws, account=account
    )
    deleted = await repo.soft_delete_message(message_id=target.id)
    if deleted is None:
        raise NotFoundError("Message not found")
    return envelope({"deleted": True}, request_id=get_request_id(request))


@router.post("/messages/read")
async def mark_messages_read(
    body: MarkChatReadRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    message_id = uuid.UUID(body.message_id)
    message = await repo.get_message(message_id)
    if message is None or message.workspace_id != ws.workspace_id:
        raise NotFoundError("Message not found")
    read_at = await repo.mark_read(
        workspace_id=ws.workspace_id, account_id=account.id, message_id=message_id
    )
    payload = ChatReadMarker(
        workspaceId=str(ws.workspace_id),
        accountId=str(account.id),
        lastReadMessageId=str(message_id),
        lastReadAt=read_at,
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.get("/messages/read")
async def get_read_marker(
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    repo = WorkspaceRepository(db)
    marker = await repo.get_read_marker(workspace_id=ws.workspace_id, account_id=account.id)
    payload = ChatReadMarker(
        workspaceId=str(ws.workspace_id),
        accountId=str(account.id),
        lastReadMessageId=str(marker.last_read_message_id) if marker and marker.last_read_message_id else None,
        lastReadAt=marker.last_read_at if marker else None,
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


@router.patch(
    "/members/{account_id}",
    dependencies=[Depends(require_capability("workspace.manage"))],
)
async def change_member_role(
    account_id: str,
    body: ChangeMemberRoleRequest,
    request: Request,
    ws: ActiveWorkspaceContext = Depends(get_active_workspace),
    account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Closes the real remove+reinvite-to-change-access gap: previously the
    only way to move a member between admin/editor/reader was removing them
    and sending a brand new invite. Mirrors remove_member's exact shape —
    same owner guard (changing the sole owner's own role is ownership
    transfer, a separate, unbuilt capability, not this endpoint), same
    workspace.manage gate, same record_activity call inside the same
    transaction as the real change."""
    target_id = uuid.UUID(account_id)
    repo = WorkspaceRepository(db)
    members = await repo.list_active_members(ws.workspace_id)
    target = next((m for m in members if m.account_id == target_id), None)
    if target is None:
        raise WorkspaceNotFoundError("Not an active member of this workspace")
    if target.role == "owner":
        raise ValidationError("The workspace owner's role cannot be changed here")
    previous_role = target.role
    updated = await repo.change_member_role(
        workspace_id=ws.workspace_id, account_id=target_id, role=body.role
    )
    if updated is None:
        raise WorkspaceNotFoundError("Not an active member of this workspace")
    await repo.record_activity(
        workspace_id=ws.workspace_id,
        event="role_changed",
        actor_account_id=account.id,
        subject_account_id=target_id,
        role=body.role,
        previous_role=previous_role,
    )
    payload = WorkspaceMemberSummary(
        accountId=str(updated.account_id), role=updated.role, joinedAt=updated.joined_at
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


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
