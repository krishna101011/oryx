"""Public Reader Rev 1 — repository structural join-safety (unit, no DB).

Proves the two READ methods the unauthenticated GET /public/pages/{slug}
router calls (PublicPagesRepository.get_by_slug / .list_citations) cannot
reach any table beyond their own, by inspecting the COMPILED SQL rather than
trusting the source by convention:

    "The public repository method must be written to SELECT only
    PublicPage's own columns — never given the ability to join outward at
    all, not merely trusted not to." (docs/PUBLIC_READER_ARCHITECTURE.md §6)

No real database is touched — a fake session just records the Select
statement passed to execute() and returns an empty result, so this test
runs in the default (no ORYX_TEST_DB) suite too.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.dialects import postgresql

from oryx.services.reader.repository import PublicPagesRepository


class _EmptyResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []


class _CapturingSession:
    def __init__(self) -> None:
        self.statements: list = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _EmptyResult()


def _only_from_table(stmt) -> str:
    froms = stmt.get_final_froms()
    assert len(froms) == 1, f"expected exactly one FROM table, got {froms}"
    return froms[0].name


def _assert_no_join(stmt) -> None:
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "JOIN" not in compiled.upper(), compiled


@pytest.mark.asyncio
async def test_get_by_slug_selects_only_public_pages_table() -> None:
    session = _CapturingSession()
    await PublicPagesRepository(session).get_by_slug(slug="whatever-slug")

    assert len(session.statements) == 1
    stmt = session.statements[0]
    assert _only_from_table(stmt) == "public_pages"
    _assert_no_join(stmt)


@pytest.mark.asyncio
async def test_list_citations_selects_only_public_page_citations_table() -> None:
    session = _CapturingSession()
    await PublicPagesRepository(session).list_citations(
        public_page_id=uuid.uuid4()
    )

    assert len(session.statements) == 1
    stmt = session.statements[0]
    assert _only_from_table(stmt) == "public_page_citations"
    _assert_no_join(stmt)


@pytest.mark.asyncio
async def test_read_methods_take_no_parameter_that_could_smuggle_a_join() -> None:
    """Both read methods accept only an opaque lookup value (slug / an
    already-known public_page_id) — neither takes a table, column, or
    relationship name, so there is no argument surface through which a
    caller could ask them to join anywhere, forbidden or not."""
    import inspect

    get_sig = inspect.signature(PublicPagesRepository.get_by_slug)
    list_sig = inspect.signature(PublicPagesRepository.list_citations)
    assert set(get_sig.parameters) == {"self", "slug"}
    assert set(list_sig.parameters) == {"self", "public_page_id"}
