"""Intake credentials repository — envelope-encrypted storage.

Every credential write goes through `store()`. Every read goes through
`load()`. The actual encryption math lives in `core/security/secrets.py`.
This module is the only place that touches the `intake_credentials` table.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anant.core.models import IntakeCredentials
from anant.core.security.secrets import (
    decrypt_for_workspace,
    encrypt_for_workspace,
    kms_version_of,
)


class CredentialPair(NamedTuple):
    token: bytes
    refresh_token: bytes | None
    token_expires_at: datetime | None
    kms_key_version: int


class IntakeCredentialsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def store(
        self,
        *,
        intake_source_id: uuid.UUID,
        workspace_id: uuid.UUID,
        token: bytes,
        refresh_token: bytes | None,
        token_expires_at: datetime | None,
        kms_key_version: int = 1,
    ) -> IntakeCredentials:
        enc_token = encrypt_for_workspace(
            token, workspace_id=workspace_id, kms_key_version=kms_key_version
        )
        enc_refresh = (
            encrypt_for_workspace(
                refresh_token,
                workspace_id=workspace_id,
                kms_key_version=kms_key_version,
            )
            if refresh_token is not None
            else None
        )
        # Upsert via fetch + replace; we keep one credentials row per source.
        result = await self.db.execute(
            select(IntakeCredentials).where(
                IntakeCredentials.intake_source_id == intake_source_id
            )
        )
        row = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if row is None:
            row = IntakeCredentials(
                id=uuid.uuid4(),
                intake_source_id=intake_source_id,
                workspace_id=workspace_id,
                encrypted_token=enc_token.blob,
                encrypted_refresh_token=enc_refresh.blob if enc_refresh else None,
                kms_key_version=kms_key_version,
                token_expires_at=token_expires_at,
            )
            self.db.add(row)
        else:
            row.encrypted_token = enc_token.blob
            row.encrypted_refresh_token = enc_refresh.blob if enc_refresh else None
            row.kms_key_version = kms_key_version
            row.token_expires_at = token_expires_at
            row.updated_at = now
        await self.db.flush()
        return row

    async def load(
        self, *, intake_source_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> CredentialPair | None:
        result = await self.db.execute(
            select(IntakeCredentials).where(
                IntakeCredentials.intake_source_id == intake_source_id,
                IntakeCredentials.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        token = decrypt_for_workspace(row.encrypted_token, workspace_id=workspace_id)
        refresh = (
            decrypt_for_workspace(row.encrypted_refresh_token, workspace_id=workspace_id)
            if row.encrypted_refresh_token
            else None
        )
        return CredentialPair(
            token=token,
            refresh_token=refresh,
            token_expires_at=row.token_expires_at,
            kms_key_version=kms_version_of(row.encrypted_token),
        )

    async def delete(
        self, *, intake_source_id: uuid.UUID
    ) -> None:
        # The DB cascade handles this; but for clarity at the API surface:
        result = await self.db.execute(
            select(IntakeCredentials).where(
                IntakeCredentials.intake_source_id == intake_source_id
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self.db.delete(row)
            await self.db.flush()
