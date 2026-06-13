"""BM25Searcher — two-stage query strategy and row mapping, via fakes.

The actual FTS SQL runs against Postgres in the integration suite; here
we verify the strategy: primary query, subject-only fallback, empty-query
guards, and CandidateItem mapping.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from anant.services.evidence.corpus_searcher import BM25Searcher
from anant.services.evidence.models import EXCERPT_CHARS


class FakeResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class FakeSession:
    """Returns canned result sets in order; records every execute()."""

    def __init__(self, result_sets: list[list]) -> None:
        self._result_sets = list(result_sets)
        self.calls: list[dict] = []

    async def execute(self, _stmt, params):
        self.calls.append(params)
        rows = self._result_sets.pop(0) if self._result_sets else []
        return FakeResult(rows)


def _row(item_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        intake_item_id=item_id or uuid.uuid4(),
        subject="Apple results",
        body_text_excerpt="Apple Inc reported revenue",
        received_at=datetime.now(UTC),
        source_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_primary_hit_skips_fallback() -> None:
    item_id = uuid.uuid4()
    session = FakeSession([[_row(item_id)]])
    result = await BM25Searcher(session).search(
        workspace_id=uuid.uuid4(),
        subject="Apple Inc",
        predicate="reported revenue of",
        exclude_intake_item_id=uuid.uuid4(),
    )
    assert len(session.calls) == 1
    assert session.calls[0]["query"] == "Apple Inc reported revenue of"
    assert session.calls[0]["excerpt_chars"] == EXCERPT_CHARS
    assert result[0].intake_item_id == item_id
    assert result[0].body_text_excerpt == "Apple Inc reported revenue"


@pytest.mark.asyncio
async def test_fallback_uses_subject_only() -> None:
    session = FakeSession([[], [_row()]])
    result = await BM25Searcher(session).search(
        workspace_id=uuid.uuid4(),
        subject="Apple Inc",
        predicate="reported revenue of",
        exclude_intake_item_id=uuid.uuid4(),
    )
    assert len(session.calls) == 2
    assert session.calls[1]["query"] == "Apple Inc"
    assert len(result) == 1


@pytest.mark.asyncio
async def test_both_stages_empty_is_valid() -> None:
    session = FakeSession([[], []])
    result = await BM25Searcher(session).search(
        workspace_id=uuid.uuid4(),
        subject="Apple Inc",
        predicate="reported",
        exclude_intake_item_id=uuid.uuid4(),
    )
    assert result == []
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_blank_predicate_runs_single_stage() -> None:
    # primary == fallback ("Apple Inc") → second stage is pointless, skipped.
    session = FakeSession([[]])
    result = await BM25Searcher(session).search(
        workspace_id=uuid.uuid4(),
        subject="Apple Inc",
        predicate="",
        exclude_intake_item_id=uuid.uuid4(),
    )
    assert result == []
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_blank_subject_and_predicate_never_queries() -> None:
    session = FakeSession([])
    result = await BM25Searcher(session).search(
        workspace_id=uuid.uuid4(),
        subject="  ",
        predicate="",
        exclude_intake_item_id=uuid.uuid4(),
    )
    assert result == []
    assert session.calls == []
