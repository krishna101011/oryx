"""Templates repository — DB operations only, no business rules."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import ContentTemplate as ContentTemplateRow

# Seed rows that ensure_default_templates inserts.
# Mirrors the migration 0010 backfill exactly.
_DEFAULT_SEED: list[tuple[str, str, int | None, int | None, str]] = [
    (
        "tweet_thread",
        "conversational",
        None,
        None,
        "Number each tweet (1/N, 2/N...). Max 280 characters per tweet. Punchy, conversational.",
    ),
    (
        "linkedin_post",
        "authoritative",
        500,
        None,
        "Professional tone. Paragraphs, not bullet lists. Max 3000 characters.",
    ),
    (
        "newsletter_section",
        "analytical",
        500,
        200,
        "Structured. Clear headline followed by body. Max 500 words.",
    ),
    (
        "article",
        "analytical",
        3000,
        800,
        "Long-form. Headline plus subheadings. 800 to 3000 words.",
    ),
    (
        "report_summary",
        "concise",
        400,
        200,
        "Executive format. Key points stated directly. 200 to 400 words.",
    ),
    (
        "custom",
        "analytical",
        None,
        None,
        "No fixed constraints. Follow analyst instructions exactly.",
    ),
]


class TemplatesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def count_for_workspace(self, workspace_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(ContentTemplateRow.id)).where(
                ContentTemplateRow.workspace_id == workspace_id
            )
        )
        return int(result.scalar_one() or 0)

    async def seed_defaults(self, workspace_id: uuid.UUID) -> None:
        """Insert all 6 default template rows. ON CONFLICT on the partial unique
        index (workspace_id, format) WHERE is_default=true → DO NOTHING.
        Safe under concurrent calls."""
        for fmt, tone, max_w, min_w, hint in _DEFAULT_SEED:
            stmt = (
                pg_insert(ContentTemplateRow)
                .values(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    name=f"Default {fmt.replace('_', ' ').title()}",
                    format=fmt,
                    tone=tone,
                    max_words=max_w,
                    min_words=min_w,
                    structure_hint=hint,
                    is_default=True,
                )
                .on_conflict_do_nothing(
                    index_elements=["workspace_id", "format"],
                    index_where=text("is_default = TRUE"),
                )
            )
            await self.db.execute(stmt)

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
        *,
        format: str | None = None,
    ) -> list[ContentTemplateRow]:
        stmt = select(ContentTemplateRow).where(
            ContentTemplateRow.workspace_id == workspace_id
        )
        if format is not None:
            stmt = stmt.where(ContentTemplateRow.format == format)
        stmt = stmt.order_by(
            ContentTemplateRow.is_default.desc(),
            ContentTemplateRow.created_at,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self, template_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> ContentTemplateRow | None:
        result = await self.db.execute(
            select(ContentTemplateRow).where(
                ContentTemplateRow.id == template_id,
                ContentTemplateRow.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, template_id: uuid.UUID) -> ContentTemplateRow | None:
        """Load without workspace check — callers must verify ownership."""
        return await self.db.get(ContentTemplateRow, template_id)

    async def get_default(
        self, workspace_id: uuid.UUID, format: str
    ) -> ContentTemplateRow | None:
        result = await self.db.execute(
            select(ContentTemplateRow).where(
                ContentTemplateRow.workspace_id == workspace_id,
                ContentTemplateRow.format == format,
                ContentTemplateRow.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def insert(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        format: str,
        tone: str,
        max_words: int | None,
        min_words: int | None,
        structure_hint: str | None,
    ) -> ContentTemplateRow:
        row = ContentTemplateRow(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            format=format,
            tone=tone,
            max_words=max_words,
            min_words=min_words,
            structure_hint=structure_hint,
            is_default=False,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def partial_update(
        self,
        template_id: uuid.UUID,
        *,
        name: str | None,
        tone: str | None,
        max_words: int | None | type[_UNSET],
        min_words: int | None | type[_UNSET],
        structure_hint: str | None | type[_UNSET],
    ) -> None:
        values: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if name is not None:
            values["name"] = name
        if tone is not None:
            values["tone"] = tone
        if max_words is not _UNSET:
            values["max_words"] = max_words
        if min_words is not _UNSET:
            values["min_words"] = min_words
        if structure_hint is not _UNSET:
            values["structure_hint"] = structure_hint
        await self.db.execute(
            update(ContentTemplateRow)
            .where(ContentTemplateRow.id == template_id)
            .values(**values)
        )

    async def delete(self, template_id: uuid.UUID) -> None:
        row = await self.db.get(ContentTemplateRow, template_id)
        if row is not None:
            await self.db.delete(row)


class _UnsetType:
    """Sentinel distinguishing "not provided" from None in partial updates."""


_UNSET = _UnsetType
