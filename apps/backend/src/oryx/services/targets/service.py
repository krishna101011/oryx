"""Publish-targets service — validate, encrypt, store, health-check.

Credentials are validated by the channel adapter BEFORE saving (invalid → 400,
nothing persisted) and encrypted (AES-256-GCM) before insert. Reads NEVER
decrypt or expose credentials (§13.2) — the router serializers omit them.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.credential_crypto import decrypt_credentials, encrypt_credentials
from oryx.core.errors import BadRequestError, NotFoundError
from oryx.core.models import PublishTarget
from oryx.services.publishing.channels.registry import get_channel
from oryx.services.targets.repository import TargetsRepository


class TargetService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def create_target(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        channel: str,
        credentials: dict[str, Any],
        config: dict[str, Any],
    ) -> PublishTarget:
        adapter = get_channel(channel)
        if not await adapter.validate_credentials(credentials):
            raise BadRequestError(
                "Channel credentials failed validation",
                details={"channel": channel},
            )
        ciphertext, iv = encrypt_credentials(credentials)
        async with self._sm() as session:
            repo = TargetsRepository(session)
            target = await repo.insert(
                workspace_id=workspace_id,
                name=name,
                channel=channel,
                credentials=ciphertext,
                credentials_iv=iv,
                config=config,
            )
            await session.commit()
            refreshed = await repo.get(
                workspace_id=workspace_id, target_id=target.id
            )
            assert refreshed is not None
            return refreshed

    async def list_targets(self, *, workspace_id: uuid.UUID) -> list[PublishTarget]:
        async with self._sm() as session:
            return await TargetsRepository(session).list_for_workspace(workspace_id)

    async def get_target(
        self, *, workspace_id: uuid.UUID, target_id: uuid.UUID
    ) -> PublishTarget:
        async with self._sm() as session:
            target = await TargetsRepository(session).get(
                workspace_id=workspace_id, target_id=target_id
            )
            if target is None:
                raise NotFoundError("Publish target not found")
            return target

    async def health_check(
        self, *, workspace_id: uuid.UUID, target_id: uuid.UUID
    ) -> bool:
        async with self._sm() as session:
            repo = TargetsRepository(session)
            target = await repo.get(
                workspace_id=workspace_id, target_id=target_id
            )
            if target is None:
                raise NotFoundError("Publish target not found")
            adapter = get_channel(target.channel)
            credentials = decrypt_credentials(
                target.credentials, target.credentials_iv
            )
            ok = await adapter.health_check(credentials)
            await repo.set_health(target_id=target_id, ok=ok)
            await session.commit()
            return ok

    async def delete_target(
        self, *, workspace_id: uuid.UUID, target_id: uuid.UUID
    ) -> None:
        async with self._sm() as session:
            repo = TargetsRepository(session)
            target = await repo.get(
                workspace_id=workspace_id, target_id=target_id
            )
            if target is None:
                raise NotFoundError("Publish target not found")
            await repo.delete(target_id=target_id)
            await session.commit()
