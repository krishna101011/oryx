"""workspaces + workspace_members + workspace_invites persistence."""
from __future__ import annotations

import hashlib
import secrets as py_secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import (
    Account,
    ChatMessage,
    Workspace,
    WorkspaceAuditLog,
    WorkspaceChatRead,
    WorkspaceInvite,
    WorkspaceMember,
)

# Real event kinds record_activity emits: member_invited, member_joined,
# member_removed, role_changed (role-change wave — the last one to gain a
# real emitter; see change_member_role below).
_ACTIVITY_LIST_LIMIT = 50

# A real, decided default — not specified by the architecture doc, chosen as
# a conventional invite lifetime (long enough for a real person to notice
# the email, short enough that a stale/leaked invite isn't a standing risk).
INVITE_TTL = timedelta(days=7)
_TOKEN_BYTES = 32


def generate_invite_token() -> str:
    """Display-once token — shown/emailed once, never persisted or logged.
    Same shape as the intake webhook secret convention."""
    return py_secrets.token_urlsafe(_TOKEN_BYTES)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WorkspaceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active_for_account(
        self, account_id: uuid.UUID
    ) -> list[tuple[Workspace, str]]:
        """Every real (workspace, role) pair this account currently, actively
        belongs to — ordered the same way _primary_workspace_id resolves a
        default (earliest joined_at first)."""
        result = await self.db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.account_id == account_id,
                WorkspaceMember.removed_at.is_(None),
            )
            .order_by(WorkspaceMember.joined_at.asc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_active_members(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        result = await self.db.execute(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.removed_at.is_(None),
            )
            .order_by(WorkspaceMember.joined_at.asc())
        )
        return list(result.scalars().all())

    async def remove_member(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """Soft-remove. Returns the removed row, or None if it wasn't an
        active member (already removed, or never one) — the caller decides
        what that means (404 vs no-op)."""
        result = await self.db.execute(
            update(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.account_id == account_id,
                WorkspaceMember.removed_at.is_(None),
            )
            .values(removed_at=datetime.now(UTC))
            .returning(WorkspaceMember)
        )
        return result.scalar_one_or_none()

    async def change_member_role(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID, role: str
    ) -> WorkspaceMember | None:
        """Returns the updated row, or None if the target wasn't an active
        member — same "caller decides what that means" contract as
        remove_member. The owner-role guard lives in the router (it needs
        the pre-update role to build the error/activity row), not here."""
        result = await self.db.execute(
            update(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.account_id == account_id,
                WorkspaceMember.removed_at.is_(None),
            )
            .values(role=role)
            .returning(WorkspaceMember)
        )
        return result.scalar_one_or_none()

    # ---- invites ----

    async def create_invite(
        self,
        *,
        workspace_id: uuid.UUID,
        invited_email: str,
        role: str,
        invited_by: uuid.UUID,
    ) -> tuple[WorkspaceInvite, str]:
        """Returns (row, raw_token) — raw_token must be emailed, never
        returned in an API response or logged; only its hash is stored."""
        raw_token = generate_invite_token()
        row = WorkspaceInvite(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            invited_email=invited_email,
            role=role,
            token_hash=hash_invite_token(raw_token),
            invited_by=invited_by,
            expires_at=datetime.now(UTC) + INVITE_TTL,
        )
        self.db.add(row)
        await self.db.flush()
        return row, raw_token

    async def get_invite_by_token(self, raw_token: str) -> WorkspaceInvite | None:
        result = await self.db.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.token_hash == hash_invite_token(raw_token)
            )
        )
        return result.scalar_one_or_none()

    async def get_invite_by_id(self, invite_id: uuid.UUID) -> WorkspaceInvite | None:
        result = await self.db.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.id == invite_id)
        )
        return result.scalar_one_or_none()

    async def list_pending_invites(
        self, workspace_id: uuid.UUID
    ) -> list[WorkspaceInvite]:
        """Not-yet-resolved invites for a workspace's Members screen: never
        accepted, never revoked. Expired-but-unactioned invites are
        deliberately included (not filtered by expires_at) — the UI renders
        the real expired state from the same fields view_invite already
        exposes, and an admin still needs to see + revoke a stale invite to
        clean it up."""
        result = await self.db.execute(
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.accepted_at.is_(None),
                WorkspaceInvite.revoked_at.is_(None),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_email_invite(
        self, *, workspace_id: uuid.UUID, invited_email: str
    ) -> WorkspaceInvite | None:
        result = await self.db.execute(
            select(WorkspaceInvite).where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.invited_email == invited_email,
                WorkspaceInvite.accepted_at.is_(None),
                WorkspaceInvite.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def accept_invite(self, invite_id: uuid.UUID) -> bool:
        """Atomic compare-and-swap: only flips accepted_at if the invite is
        STILL pending AND unexpired at the moment this runs (expires_at is
        part of the same WHERE, not checked separately beforehand — an
        invite that expires between the caller's earlier read and this
        UPDATE must not be accepted just because it looked valid a moment
        ago). Postgres re-evaluates an UPDATE's WHERE clause against the
        committed row once a blocking concurrent UPDATE on the same row
        releases its lock — so of two concurrent accept attempts on the
        same token, exactly one UPDATE matches (rowcount 1) and the other
        matches zero rows. This is what makes a real double-accept race safe
        without any extra locking."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            update(WorkspaceInvite)
            .where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.accepted_at.is_(None),
                WorkspaceInvite.revoked_at.is_(None),
                WorkspaceInvite.expires_at > now,
            )
            .values(accepted_at=now)
        )
        return result.rowcount == 1

    async def get_active_member_by_email(
        self, *, workspace_id: uuid.UUID, email: str
    ) -> WorkspaceMember | None:
        """Pre-check for invite creation: is this email already an active
        member of this workspace?"""
        result = await self.db.execute(
            select(WorkspaceMember)
            .join(Account, Account.id == WorkspaceMember.account_id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.removed_at.is_(None),
                Account.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def revoke_invite(self, invite_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            update(WorkspaceInvite)
            .where(
                WorkspaceInvite.id == invite_id,
                WorkspaceInvite.accepted_at.is_(None),
                WorkspaceInvite.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        return result.rowcount == 1

    async def join_workspace(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID, role: str, invited_by: uuid.UUID
    ) -> datetime:
        """Creates or REACTIVATES the real WorkspaceMember row. An upsert,
        not a plain INSERT: the composite PK is (workspace_id, account_id),
        so a previously-removed member accepting a new invite to the same
        workspace would otherwise collide with their own soft-deleted row
        instead of reactivating it."""
        now = datetime.now(UTC)
        stmt = (
            pg_insert(WorkspaceMember)
            .values(
                workspace_id=workspace_id,
                account_id=account_id,
                role=role,
                invited_by=invited_by,
                joined_at=now,
                removed_at=None,
            )
            .on_conflict_do_update(
                index_elements=["workspace_id", "account_id"],
                set_={
                    "role": role,
                    "invited_by": invited_by,
                    "joined_at": now,
                    "removed_at": None,
                },
            )
        )
        await self.db.execute(stmt)
        return now

    # ---- activity log (Team nav promotion wave) ----

    async def record_activity(
        self,
        *,
        workspace_id: uuid.UUID,
        event: str,
        actor_account_id: uuid.UUID | None = None,
        subject_account_id: uuid.UUID | None = None,
        subject_email: str | None = None,
        role: str | None = None,
        previous_role: str | None = None,
    ) -> None:
        """Inserts inside the CALLER's transaction — no commit here, same
        convention as core/audit.py's record_auth_event. Always call this
        from the same request handler that just made the real membership
        change, after the change succeeded. `previous_role` is only ever set
        by the role_changed caller (migration 0033) — every other event
        leaves it null."""
        self.db.add(
            WorkspaceAuditLog(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                event=event,
                actor_account_id=actor_account_id,
                subject_account_id=subject_account_id,
                subject_email=subject_email,
                role=role,
                previous_role=previous_role,
            )
        )
        await self.db.flush()

    async def list_activity(self, workspace_id: uuid.UUID) -> list[WorkspaceAuditLog]:
        """Most-recent-first, capped at _ACTIVITY_LIST_LIMIT — the Team
        Activity view has no pagination UI yet, so this mirrors
        list_pending_invites' simple unpaginated shape rather than
        inventing cursor support nothing consumes."""
        result = await self.db.execute(
            select(WorkspaceAuditLog)
            .where(WorkspaceAuditLog.workspace_id == workspace_id)
            .order_by(WorkspaceAuditLog.created_at.desc())
            .limit(_ACTIVITY_LIST_LIMIT)
        )
        return list(result.scalars().all())

    # ---- chat (Team Chat foundation wave) ----
    #
    # Deliberately NOT modeled on list_activity above: that method is the
    # unpaginated "latest 50" shape recon flagged as unfit for real message
    # history. list_latest_messages/list_messages_after together give a real,
    # stable cursor over (created_at, id) — see ChatMessage's docstring in
    # core/models.py for why the compound order matters.

    async def send_message(
        self, *, workspace_id: uuid.UUID, sender_account_id: uuid.UUID, body: str
    ) -> ChatMessage:
        row = ChatMessage(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            sender_account_id=sender_account_id,
            body=body,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_message(self, message_id: uuid.UUID) -> ChatMessage | None:
        result = await self.db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_latest_messages(
        self, *, workspace_id: uuid.UUID, limit: int
    ) -> list[ChatMessage]:
        """The initial page: the most recent `limit` messages, returned in
        chronological (ascending) order so a client can render them
        top-to-bottom directly. Fetched DESC (to get the recent end) then
        reversed in Python — the ORDER BY DESC ... LIMIT is what makes this
        a bounded, indexed query rather than a full table scan."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.workspace_id == workspace_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def list_messages_after(
        self,
        *,
        workspace_id: uuid.UUID,
        after_created_at: datetime,
        after_id: uuid.UUID,
        limit: int,
    ) -> list[ChatMessage]:
        """The poll path: every message strictly newer than (after_created_at,
        after_id) — the compound comparison is what makes a cursor safe when
        two messages tie on created_at (same-millisecond sends), matching the
        ORDER BY below so a row is never skipped or re-delivered."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.workspace_id == workspace_id,
                or_(
                    ChatMessage.created_at > after_created_at,
                    and_(
                        ChatMessage.created_at == after_created_at,
                        ChatMessage.id > after_id,
                    ),
                ),
            )
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def edit_message(
        self, *, message_id: uuid.UUID, body: str
    ) -> ChatMessage | None:
        """Returns the updated row, or None if it wasn't an editable message
        (missing or already soft-deleted) — same "caller decides what that
        means" contract as change_member_role. The sender-ownership check
        happens in the router (it needs the pre-update row to build the
        403/404 distinction), not here."""
        result = await self.db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == message_id, ChatMessage.deleted_at.is_(None))
            .values(body=body, edited_at=datetime.now(UTC))
            .returning(ChatMessage)
        )
        return result.scalar_one_or_none()

    async def soft_delete_message(self, *, message_id: uuid.UUID) -> ChatMessage | None:
        result = await self.db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == message_id, ChatMessage.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
            .returning(ChatMessage)
        )
        return result.scalar_one_or_none()

    async def mark_read(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID, message_id: uuid.UUID
    ) -> datetime:
        """Upsert — same on_conflict_do_update shape as join_workspace above."""
        now = datetime.now(UTC)
        stmt = (
            pg_insert(WorkspaceChatRead)
            .values(
                workspace_id=workspace_id,
                account_id=account_id,
                last_read_message_id=message_id,
                last_read_at=now,
            )
            .on_conflict_do_update(
                index_elements=["workspace_id", "account_id"],
                set_={"last_read_message_id": message_id, "last_read_at": now},
            )
        )
        await self.db.execute(stmt)
        return now

    async def get_read_marker(
        self, *, workspace_id: uuid.UUID, account_id: uuid.UUID
    ) -> WorkspaceChatRead | None:
        result = await self.db.execute(
            select(WorkspaceChatRead).where(
                WorkspaceChatRead.workspace_id == workspace_id,
                WorkspaceChatRead.account_id == account_id,
            )
        )
        return result.scalar_one_or_none()
