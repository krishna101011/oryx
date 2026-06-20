"""BM25-style corpus search over intake_items_normalized.

Uses PostgreSQL full-text search through the GIN expression index created
in Wave A (idx_intake_normalized_fts) — the tsvector expression below must
stay byte-identical to the index definition or the planner won't use it.

intake_items_normalized carries no workspace column, so every query joins
intake_items for tenant scoping, received_at, and the source id.

Two-stage strategy:
  1. subject + predicate terms
  2. fallback: subject terms only (if stage 1 returns nothing)
  3. empty result is valid — the corpus may be sparse at Phase 4 launch
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from oryx.services.evidence.models import EXCERPT_CHARS, CandidateItem

DEFAULT_LIMIT = 20

# The tsvector expression mirrors idx_intake_normalized_fts exactly.
_SEARCH_SQL = text(
    """
    SELECT
        i.id              AS intake_item_id,
        n.subject         AS subject,
        LEFT(coalesce(n.body_text, ''), :excerpt_chars) AS body_text_excerpt,
        i.received_at     AS received_at,
        i.intake_source_id AS source_id
    FROM intake_items_normalized n
    JOIN intake_items i ON i.id = n.intake_item_id
    WHERE i.workspace_id = :workspace_id
      AND i.id != :exclude_intake_item_id
      AND i.deleted_at IS NULL
      AND to_tsvector('english',
            coalesce(n.subject,'') || ' ' || coalesce(n.body_text,''))
          @@ plainto_tsquery('english', :query)
    ORDER BY ts_rank(
        to_tsvector('english',
            coalesce(n.subject,'') || ' ' || coalesce(n.body_text,'')),
        plainto_tsquery('english', :query)
    ) DESC
    LIMIT :limit
    """
)


class BM25Searcher:
    """Stateless; one instance per request is fine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        *,
        workspace_id: uuid.UUID,
        subject: str,
        predicate: str,
        exclude_intake_item_id: uuid.UUID,
        limit: int = DEFAULT_LIMIT,
    ) -> list[CandidateItem]:
        primary = f"{subject} {predicate}".strip()
        candidates = await self._run(
            workspace_id=workspace_id,
            query=primary,
            exclude_intake_item_id=exclude_intake_item_id,
            limit=limit,
        )
        if candidates:
            return candidates
        # Fallback: subject-only terms.
        fallback = subject.strip()
        if not fallback or fallback == primary:
            return []
        return await self._run(
            workspace_id=workspace_id,
            query=fallback,
            exclude_intake_item_id=exclude_intake_item_id,
            limit=limit,
        )

    async def _run(
        self,
        *,
        workspace_id: uuid.UUID,
        query: str,
        exclude_intake_item_id: uuid.UUID,
        limit: int,
    ) -> list[CandidateItem]:
        if not query.strip():
            return []  # plainto_tsquery('') matches nothing anyway
        result = await self.db.execute(
            _SEARCH_SQL,
            {
                "workspace_id": str(workspace_id),
                "exclude_intake_item_id": str(exclude_intake_item_id),
                "query": query,
                "limit": limit,
                "excerpt_chars": EXCERPT_CHARS,
            },
        )
        return [
            CandidateItem(
                intake_item_id=row.intake_item_id,
                subject=row.subject,
                body_text_excerpt=row.body_text_excerpt or "",
                received_at=row.received_at,
                source_id=row.source_id,
            )
            for row in result.all()
        ]
