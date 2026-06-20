"""Auth service — business logic.

Orchestrates account creation, session rotation, password ops.
Does NOT contain HTTP concerns. Does NOT call providers directly outside its
declared interfaces.

Atomic signup: create_account + create_workspace + create_workspace_member +
create_profile + create_preferences + create_onboarding_state must all succeed
or all roll back. The caller (the router) opens a single DB session and we
add all rows to it; the session's commit-on-success contract enforces atomicity.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.config import get_settings
from oryx.core.audit import record_auth_event
from oryx.core.errors import (
    AuthAccountLockedError,
    AuthEmailTakenError,
    AuthInvalidCredentialsError,
    AuthRefreshInvalidError,
    AuthRefreshReuseDetectedError,
)
from oryx.core.models import (
    OnboardingState,
    Preferences,
    Profile,
    Workspace,
    WorkspaceMember,
)
from oryx.core.security.jwt import issue_access_token
from oryx.core.security.passwords import (
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    validate_password,
    verify_password,
)
from oryx.services.auth.repository import AuthRepository


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime
    session_id: uuid.UUID
    account_id: uuid.UUID


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuthRepository(db)
        self.settings = get_settings()

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------
    async def signup(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        device_id: str,
        device_label: str,
        device_platform: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> IssuedTokens:
        validate_password(password)

        if await self.repo.get_account_by_email(email):
            raise AuthEmailTakenError()

        account = await self.repo.create_account(
            email=email, password_hash=hash_password(password)
        )

        # Workspace + membership + profile + preferences + onboarding (all atomic).
        workspace = Workspace(
            id=uuid.uuid4(),
            name=f"{display_name}'s Workspace",
            kind="personal",
            owner_account_id=account.id,
            plan="free",
        )
        self.db.add(workspace)
        await self.db.flush()

        self.db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                account_id=account.id,
                role="owner",
            )
        )
        self.db.add(
            Profile(
                account_id=account.id,
                display_name=display_name,
                timezone="UTC",
                locale="en-US",
            )
        )
        self.db.add(
            Preferences(
                account_id=account.id,
                focus="both",
                content_style="balanced",
                verification_strictness="balanced",
                notification_frequency="daily",
                custom_topics=[],
            )
        )
        self.db.add(
            OnboardingState(
                account_id=account.id,
                current_step="welcome",
            )
        )

        tokens = await self._issue_session(
            account_id=account.id,
            workspace_id=workspace.id,
            device_id=device_id,
            device_label=device_label,
            device_platform=device_platform,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await record_auth_event(
            self.db,
            event="signup",
            account_id=account.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return tokens

    # ------------------------------------------------------------------
    # Signin
    # ------------------------------------------------------------------
    async def signin(
        self,
        *,
        email: str,
        password: str,
        device_id: str,
        device_label: str,
        device_platform: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> IssuedTokens:
        account = await self.repo.get_account_by_email(email)

        # Use constant-ish-time comparison even if account missing: hash a dummy
        # password to keep timing similar regardless of email enumeration.
        if account is None:
            verify_password(
                "$argon2id$v=19$m=65536,t=3,p=2$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                password,
            )
            raise AuthInvalidCredentialsError()

        now = datetime.now(UTC)
        if account.locked_until and account.locked_until > now:
            raise AuthAccountLockedError(
                details={"until": account.locked_until.isoformat()}
            )

        if not verify_password(account.password_hash, password):
            failed = await self.repo.increment_failed_login(account.id)
            if failed >= self.settings.lockout_threshold:
                lock_until = now + timedelta(minutes=self.settings.lockout_minutes)
                await self.repo.lock_account(account.id, lock_until)
                await record_auth_event(
                    self.db,
                    event="lockout",
                    account_id=account.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    data={"until": lock_until.isoformat()},
                )
            await record_auth_event(
                self.db,
                event="signin_failure",
                account_id=account.id,
                ip_address=ip_address,
                user_agent=user_agent,
                data={"reason": "invalid_password"},
            )
            # The raise below rolls the request transaction back; the failed
            # counter, lockout, and audit rows must survive it or lockout
            # can never trigger.
            await self.db.commit()
            raise AuthInvalidCredentialsError()

        await self.repo.reset_failed_login(account.id)

        # Resolve the user's workspace (single workspace in Phase 2).
        workspace_id = await self._primary_workspace_id(account.id)

        tokens = await self._issue_session(
            account_id=account.id,
            workspace_id=workspace_id,
            device_id=device_id,
            device_label=device_label,
            device_platform=device_platform,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await record_auth_event(
            self.db,
            event="signin_success",
            account_id=account.id,
            ip_address=ip_address,
            user_agent=user_agent,
            data={"session_id": str(tokens.session_id)},
        )
        return tokens

    # ------------------------------------------------------------------
    # Refresh (with reuse detection)
    # ------------------------------------------------------------------
    async def refresh(
        self,
        *,
        refresh_token: str,
        device_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> IssuedTokens:
        token_hash = hash_refresh_token(refresh_token)
        session_row = await self.repo.get_session_by_refresh_hash(token_hash)
        if session_row is None:
            raise AuthRefreshInvalidError()

        now = datetime.now(UTC)

        # Reuse detection: a presented but already-revoked refresh token means
        # someone has stolen the token from a rotated chain. Revoke the whole chain.
        if session_row.revoked_at is not None:
            await self.repo.revoke_chain(session_row.id, reason="reuse_detected")
            await record_auth_event(
                self.db,
                event="refresh_reuse_detected",
                account_id=session_row.account_id,
                ip_address=ip_address,
                user_agent=user_agent,
                data={"session_chain_root": str(session_row.id)},
            )
            # Same rollback hazard as signin failures: the chain revocation
            # is the security response and must outlive the 401.
            await self.db.commit()
            raise AuthRefreshReuseDetectedError()

        if session_row.expires_at < now:
            raise AuthRefreshInvalidError("Refresh expired")

        if session_row.device_id != device_id:
            raise AuthRefreshInvalidError("Device mismatch")

        # Rotate: revoke old, mint new linked via parent_session_id.
        await self.repo.revoke_session(session_row.id, reason="rotation")

        workspace_id = await self._primary_workspace_id(session_row.account_id)
        tokens = await self._issue_session(
            account_id=session_row.account_id,
            workspace_id=workspace_id,
            device_id=session_row.device_id,
            device_label=session_row.device_label,
            device_platform=session_row.device_platform,
            ip_address=ip_address,
            user_agent=user_agent,
            parent_session_id=session_row.id,
        )
        await record_auth_event(
            self.db,
            event="refresh",
            account_id=session_row.account_id,
            ip_address=ip_address,
            user_agent=user_agent,
            data={
                "old_session_id": str(session_row.id),
                "new_session_id": str(tokens.session_id),
            },
        )
        return tokens

    # ------------------------------------------------------------------
    # Signout
    # ------------------------------------------------------------------
    async def signout(
        self, *, session_id: uuid.UUID, account_id: uuid.UUID
    ) -> None:
        await self.repo.revoke_session(session_id, reason="user_signout")
        await record_auth_event(
            self.db,
            event="signout",
            account_id=account_id,
            data={"session_id": str(session_id)},
        )

    async def signout_all(self, *, account_id: uuid.UUID) -> None:
        await self.repo.revoke_all_for_account(account_id, reason="user_signout_all")
        await record_auth_event(
            self.db, event="signout_all", account_id=account_id
        )

    # ------------------------------------------------------------------
    # Password change
    # ------------------------------------------------------------------
    async def change_password(
        self, *, account_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        account = await self.repo.get_account_by_id(account_id)
        if account is None or not verify_password(account.password_hash, current_password):
            raise AuthInvalidCredentialsError()
        validate_password(new_password)
        await self.repo.update_password(account_id, hash_password(new_password))
        await record_auth_event(
            self.db, event="password_change", account_id=account_id
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _primary_workspace_id(self, account_id: uuid.UUID) -> uuid.UUID:
        result = await self.db.execute(
            select(WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.account_id == account_id,
                WorkspaceMember.removed_at.is_(None),
            )
            .limit(1)
        )
        wsp = result.scalar_one_or_none()
        if wsp is None:
            # Should be impossible post-signup; defensive.
            raise AuthInvalidCredentialsError("No workspace membership")
        return wsp

    async def _issue_session(
        self,
        *,
        account_id: uuid.UUID,
        workspace_id: uuid.UUID,
        device_id: str,
        device_label: str,
        device_platform: str,
        ip_address: str | None,
        user_agent: str | None,
        parent_session_id: uuid.UUID | None = None,
    ) -> IssuedTokens:
        refresh_token = generate_refresh_token()
        refresh_hash = hash_refresh_token(refresh_token)
        refresh_expires_at = datetime.now(UTC) + timedelta(
            days=self.settings.refresh_token_ttl_days
        )

        session_row = await self.repo.create_session(
            account_id=account_id,
            refresh_token_hash=refresh_hash,
            device_id=device_id,
            device_label=device_label,
            device_platform=device_platform,
            expires_at=refresh_expires_at,
            parent_session_id=parent_session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        access_token, access_expires_at = issue_access_token(
            account_id=str(account_id),
            workspace_id=str(workspace_id),
            session_id=str(session_row.id),
        )

        return IssuedTokens(
            access_token=access_token,
            access_token_expires_at=access_expires_at,
            refresh_token=refresh_token,
            refresh_token_expires_at=refresh_expires_at,
            session_id=session_row.id,
            account_id=account_id,
        )
