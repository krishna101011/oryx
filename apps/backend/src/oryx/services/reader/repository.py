"""Public pages repository — DB operations only, no business rules.

Two DISTINCT access patterns live here on purpose:

  - create() / get_by_draft() are the WRITE side, called by the publishing
    engine from inside its own transaction. They may read whatever the
    engine's session can already see.

  - get_by_slug() / list_citations() are the READ side: the ONLY two calls
    the unauthenticated GET /public/pages/{slug} router makes. Each SELECTs
    exclusively from its own table's own columns — neither has a join
    clause — so they are structurally unable to reach intelligence_objects,
    claims, publish_targets, or any other workspace-internal table, not
    merely trusted by convention not to (docs/PUBLIC_READER_ARCHITECTURE.md
    §6).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.core.models import PublicPage, PublicPageCitation
from oryx.services.reader.slugs import generate_public_page_slug

_MAX_SLUG_ATTEMPTS = 5


class PublicPagesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------------- write side (engine hook) ----------------

    async def create(
        self,
        *,
        content_draft_id: uuid.UUID,
        workspace_id: uuid.UUID,
        content_snapshot: str,
    ) -> PublicPage:
        """Insert a public_pages row for this draft, or return the existing
        one if it already has one — ON CONFLICT DO NOTHING on
        UNIQUE(content_draft_id) mirrors PublicationsRepository.ensure_pending's
        race-safety (the engine's own "already published" status guard makes
        concurrent calls rare, not impossible).

        A slug collision (UNIQUE(slug)) is retried a handful of times inside
        a SAVEPOINT, so it can never abort the caller's outer transaction —
        at 12 nanoid characters this is a purely mechanical safety net, not
        an expected code path.
        """
        for _ in range(_MAX_SLUG_ATTEMPTS):
            slug = generate_public_page_slug()
            try:
                async with self.db.begin_nested():
                    stmt = (
                        pg_insert(PublicPage)
                        .values(
                            id=uuid.uuid4(),
                            content_draft_id=content_draft_id,
                            workspace_id=workspace_id,
                            slug=slug,
                            content_snapshot=content_snapshot,
                        )
                        .on_conflict_do_nothing(
                            index_elements=["content_draft_id"]
                        )
                    )
                    await self.db.execute(stmt)
            except IntegrityError:
                continue  # slug collision — retry with a fresh slug
            break
        else:
            raise RuntimeError(
                "Could not allocate a unique public-page slug after "
                f"{_MAX_SLUG_ATTEMPTS} attempts"
            )

        existing = await self.get_by_draft(content_draft_id=content_draft_id)
        assert existing is not None
        return existing

    async def get_by_draft(
        self, *, content_draft_id: uuid.UUID
    ) -> PublicPage | None:
        result = await self.db.execute(
            select(PublicPage).where(
                PublicPage.content_draft_id == content_draft_id
            )
        )
        return result.scalar_one_or_none()

    # ---------------- read side (public, unauthenticated) ----------------

    async def get_by_slug(self, *, slug: str) -> PublicPage | None:
        result = await self.db.execute(
            select(PublicPage).where(PublicPage.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_citations(
        self, *, public_page_id: uuid.UUID
    ) -> list[PublicPageCitation]:
        result = await self.db.execute(
            select(PublicPageCitation)
            .where(PublicPageCitation.public_page_id == public_page_id)
            .order_by(
                PublicPageCitation.confidence_score.desc().nulls_last(),
                PublicPageCitation.intelligence_object_id,
            )
        )
        return list(result.scalars().all())
