"""workspaces + workspace_members + workspace_invites persistence."""
from __future__ import annotations

import hashlib
import secrets as py_secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import Account, Workspace, WorkspaceInvite, WorkspaceMember

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
