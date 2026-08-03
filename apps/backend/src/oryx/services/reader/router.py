"""Public Reader Rev 1 endpoint (docs/PUBLIC_READER_ARCHITECTURE.md §6) —
backend foundation only, no frontend rendering yet.

GET /public/pages/{slug} is deliberately unauthenticated — no
require_capability, no get_active_workspace, no CurrentPrincipal — the same
shape as services/health/router.py, because there is no principal and no
workspace context for an anonymous reader.

The response is an explicit allow-list, not a deny-list (§6): content plus
the exact five provenance fields the doc names — headline, epistemicType,
confidenceScore, scoringVersion, snapshottedAt — and nothing else. In
particular PublicPage.workspace_id and PublicPage.content_draft_id are read
by the repository but never serialized into this payload.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from oryx.core.db import get_sessionmaker
from oryx.core.dependencies import envelope, get_request_id
from oryx.core.errors import NotFoundError
from oryx.services.reader.repository import PublicPagesRepository

router = APIRouter(tags=["reader"])


@router.get("/public/pages/{slug}")
async def get_public_page(slug: str, request: Request) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        repo = PublicPagesRepository(session)
        page = await repo.get_by_slug(slug=slug)
        if page is None:
            raise NotFoundError("Page not found")
        citations = await repo.list_citations(public_page_id=page.id)

    payload = {
        "content": page.content_snapshot,
        "publishedAt": page.published_at.isoformat(),
        "citations": [
            {
                "headline": c.headline,
                "epistemicType": c.epistemic_type,
                "confidenceScore": c.confidence_score,
                "scoringVersion": c.scoring_version,
                "snapshottedAt": c.snapshotted_at.isoformat(),
            }
            for c in citations
        ],
    }
    return envelope(payload, request_id=get_request_id(request))
