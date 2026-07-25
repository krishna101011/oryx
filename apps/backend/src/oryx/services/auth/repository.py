"""Auth repository — accounts + sessions persistence."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import Account, WorkspaceMember
from oryx.core.models import Session as SessionRow


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---- accounts ----
    async def get_account_by_email(self, email: str) -> Account | None:
        result = await self.db.execute(select(Account).where(Account.email == email))
        return result.scalar_one_or_none()

    async def get_account_by_id(self, account_id: uuid.UUID) -> Account | None:
        result = await self.db.execute(select(Account).where(Account.id == account_id))
        return result.scalar_one_or_none()

    async def create_account(
        self, *, email: str, password_hash: str
    ) -> Account:
        account = Account(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        self.db.add(account)
        await self.db.flush()
        return account

    async def update_password(
        self, account_id: uuid.UUID, password_hash: str
    ) -> None:
        await self.db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(
                password_hash=password_hash,
                password_changed_at=datetime.now(UTC),
            )
        )

    async def increment_failed_login(self, account_id: uuid.UUID) -> int:
        result = await self.db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(failed_login_count=Account.failed_login_count + 1)
            .returning(Account.failed_login_count)
        )
        scalar = result.scalar_one_or_none()
        return int(scalar) if scalar is not None else 0

    async def reset_failed_login(self, account_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(
                failed_login_count=0,
                last_login_at=datetime.now(UTC),
            )
        )

    async def lock_account(
        self, account_id: uuid.UUID, until: datetime
    ) -> None:
        await self.db.execute(
            update(Account).where(Account.id == account_id).values(locked_until=until)
        )

    # ---- sessions ----
    async def create_session(
        self,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        refresh_token_hash: str,
        device_id: str,
        device_label: str,
        device_platform: str,
        expires_at: datetime,
        parent_session_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SessionRow:
        row = SessionRow(
            id=uuid.uuid4(),
            account_id=account_id,
            workspace_id=workspace_id,
            refresh_token_hash=refresh_token_hash,
            parent_session_id=parent_session_id,
            device_id=device_id,
            device_label=device_label,
            device_platform=device_platform,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_session_by_refresh_hash(
        self, refresh_hash: str
    ) -> SessionRow | None:
        result = await self.db.execute(
            select(SessionRow).where(SessionRow.refresh_token_hash == refresh_hash)
        )
        return result.scalar_one_or_none()

    async def get_active_membership(
        self, *, account_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceMember | None:
        """Real membership check for workspace switching — mirrors
        core/dependencies.py's get_active_workspace so switch_workspace()
        can never mint a token for a workspace the account doesn't
        genuinely (still) belong to."""
        result = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.account_id == account_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.removed_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_session(
        self, session_id: uuid.UUID, reason: str
    ) -> None:
        await self.db.execute(
            update(SessionRow)
            .where(SessionRow.id == session_id, SessionRow.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )

    async def revoke_chain(
        self, root_session_id: uuid.UUID, reason: str
    ) -> None:
        """Revoke a session and every descendant via parent_session_id."""
        # Walk descendants iteratively (Phase 2: chains are shallow; depth ~= TTL/15min).
        to_revoke = {root_session_id}
        frontier = [root_session_id]
        while frontier:
            result = await self.db.execute(
                select(SessionRow.id).where(
                    SessionRow.parent_session_id.in_(frontier)
                )
            )
            children = [r[0] for r in result.all()]
            children = [c for c in children if c not in to_revoke]
            if not children:
                break
            to_revoke.update(children)
            frontier = children
        if to_revoke:
            await self.db.execute(
                update(SessionRow)
                .where(SessionRow.id.in_(to_revoke), SessionRow.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
            )

    async def revoke_all_for_account(
        self, account_id: uuid.UUID, reason: str
    ) -> None:
        await self.db.execute(
            update(SessionRow)
            .where(
                SessionRow.account_id == account_id,
                SessionRow.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )

    async def list_active_sessions(
        self, account_id: uuid.UUID
    ) -> list[SessionRow]:
        result = await self.db.execute(
            select(SessionRow)
            .where(
                SessionRow.account_id == account_id,
                SessionRow.revoked_at.is_(None),
            )
            .order_by(SessionRow.last_used_at.desc())
        )
        return list(result.scalars().all())
