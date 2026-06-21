"""Templates service — template management and resolution.

resolve_template is the single authoritative path for obtaining a ContentTemplate
to use in generation and format-switching. Nothing else resolves templates.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.errors import BadRequestError, NotFoundError, PreconditionFailedError
from oryx.core.logging import get_logger
from oryx.services.templates.models import ContentTemplate
from oryx.services.templates.repository import _UNSET, TemplatesRepository

logger = get_logger(__name__)


def _to_domain(row) -> ContentTemplate:  # type: ignore[no-untyped-def]
    return ContentTemplate(
        id=row.id,
        workspace_id=row.workspace_id,
        name=row.name,
        format=row.format,
        tone=row.tone,
        max_words=row.max_words,
        min_words=row.min_words,
        structure_hint=row.structure_hint,
        is_default=row.is_default,
    )


class TemplateService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def ensure_default_templates(
        self, workspace_id: uuid.UUID, session: AsyncSession
    ) -> None:
        """Insert default templates for each format. Idempotent under concurrent
        calls — the partial UNIQUE index (workspace_id, format) WHERE is_default=true
        handles the conflict at the DB layer with ON CONFLICT DO NOTHING."""
        repo = TemplatesRepository(session)
        await repo.seed_defaults(workspace_id)

    async def list_templates(
        self,
        workspace_id: uuid.UUID,
        *,
        format: str | None = None,
        session: AsyncSession,
    ) -> list[ContentTemplate]:
        """List templates, lazy-seeding defaults on first access."""
        repo = TemplatesRepository(session)
        count = await repo.count_for_workspace(workspace_id)
        if count == 0:
            await self.ensure_default_templates(workspace_id, session)
            await session.flush()
        rows = await repo.list_for_workspace(workspace_id, format=format)
        return [_to_domain(r) for r in rows]

    async def get_template(
        self, template_id: uuid.UUID, workspace_id: uuid.UUID, *, session: AsyncSession
    ) -> ContentTemplate:
        repo = TemplatesRepository(session)
        row = await repo.get(template_id, workspace_id)
        if row is None:
            raise NotFoundError("Template not found")
        return _to_domain(row)

    async def create_template(
        self,
        workspace_id: uuid.UUID,
        *,
        name: str,
        format: str,
        tone: str,
        max_words: int | None,
        min_words: int | None,
        structure_hint: str | None,
        session: AsyncSession,
    ) -> ContentTemplate:
        repo = TemplatesRepository(session)
        row = await repo.insert(
            workspace_id=workspace_id,
            name=name,
            format=format,
            tone=tone,
            max_words=max_words,
            min_words=min_words,
            structure_hint=structure_hint,
        )
        return _to_domain(row)

    async def update_template(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        *,
        name: str | None = None,
        tone: str | None = None,
        max_words: int | None | type[_UNSET] = _UNSET,
        min_words: int | None | type[_UNSET] = _UNSET,
        structure_hint: str | None | type[_UNSET] = _UNSET,
        is_default_attempted: bool = False,
        session: AsyncSession,
    ) -> ContentTemplate:
        if is_default_attempted:
            raise BadRequestError(
                "is_default is system-managed and cannot be set via this endpoint"
            )
        repo = TemplatesRepository(session)
        row = await repo.get(template_id, workspace_id)
        if row is None:
            raise NotFoundError("Template not found")
        await repo.partial_update(
            template_id,
            name=name,
            tone=tone,
            max_words=max_words,
            min_words=min_words,
            structure_hint=structure_hint,
        )
        await session.flush()
        refreshed = await repo.get(template_id, workspace_id)
        assert refreshed is not None
        return _to_domain(refreshed)

    async def delete_template(
        self,
        template_id: uuid.UUID,
        workspace_id: uuid.UUID,
        *,
        session: AsyncSession,
    ) -> None:
        repo = TemplatesRepository(session)
        row = await repo.get(template_id, workspace_id)
        if row is None:
            raise NotFoundError("Template not found")
        if row.is_default:
            raise PreconditionFailedError(
                "Default templates cannot be deleted"
            )
        await repo.delete(template_id)

    async def resolve_template(
        self,
        workspace_id: uuid.UUID,
        format: str,
        template_id: uuid.UUID | None,
        session: AsyncSession,
    ) -> ContentTemplate:
        """Single authoritative resolution path used by both generation and
        format-switching. Never duplicated in callers.

        With template_id:
          - load it; verify workspace ownership (404 if wrong workspace)
          - verify format matches (400 if not)
        Without template_id:
          - ensure defaults exist (lazy seed)
          - return the default for the requested format
        """
        repo = TemplatesRepository(session)
        if template_id is not None:
            row = await repo.get_by_id(template_id)
            if row is None or row.workspace_id != workspace_id:
                raise NotFoundError("Template not found")
            if row.format != format:
                raise BadRequestError(
                    "Template format does not match requested format",
                    details={"template_format": row.format, "requested_format": format},
                )
            return _to_domain(row)

        # No template_id — lazy seed then return the default.
        count = await repo.count_for_workspace(workspace_id)
        if count == 0:
            await self.ensure_default_templates(workspace_id, session)
            await session.flush()
        row = await repo.get_default(workspace_id, format)
        if row is None:
            # Workspace exists but default is somehow missing — seed it.
            await self.ensure_default_templates(workspace_id, session)
            await session.flush()
            row = await repo.get_default(workspace_id, format)
        if row is None:
            raise NotFoundError(
                f"No default template found for format '{format}'"
            )
        return _to_domain(row)
