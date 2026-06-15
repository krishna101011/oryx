"""Source-credibility bootstrap against Postgres (Phase 4 Wave C, ADR-031).

Pins the arithmetic that migration 0006 depends on:
  - a catalog source with editorial_confidence 75 bootstraps to accuracy 0.75
    (NOT 0 — the `::float` cast defeats Postgres integer division), and
  - a source with no catalog match falls back to the neutral prior 0.5.

The INSERT below is the SAME statement migration 0006 runs; we replay it over
freshly seeded sources because the migration already executed at upgrade time.

Runs only when ANANT_TEST_DB is set (with migrations applied).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text

pytestmark = pytest.mark.requires_db

# Verbatim from alembic/versions/0006_phase4_wave_c.py — keep in sync.
BOOTSTRAP_SQL = text(
    """
    INSERT INTO source_credibility_records
        (workspace_id, source_id, accuracy_rate, updated_at)
    SELECT s.workspace_id,
           s.id,
           COALESCE(sc.editorial_confidence, 50)::float / 100.0,
           NOW()
    FROM intake_sources s
    LEFT JOIN source_catalog sc
           ON s.origin_kind = 'catalog'
          AND sc.key = s.origin_catalog_key
    WHERE s.deleted_at IS NULL
    ON CONFLICT (workspace_id, source_id) DO NOTHING
    """
)


@pytest.mark.asyncio
async def test_bootstrap_maps_editorial_confidence_and_neutral_prior(sm) -> None:
    from anant.core.models import (
        Account,
        IntakeSource,
        SourceCatalog,
        SourceCredibilityRecord,
        Workspace,
    )

    marker = uuid.uuid4().hex[:8]
    catalog_key = f"cat-{marker}"

    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"boot+{marker}@anant.test",
            password_hash="x",
            password_changed_at=datetime.now(UTC),
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Bootstrap WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()

        session.add(
            SourceCatalog(
                key=catalog_key,
                name="Catalog Feed",
                url="https://example.test/feed",
                focus="markets",
                editorial_confidence=75,
            )
        )
        await session.flush()

        catalog_source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="rss",
            name="catalog source",
            enabled=True,
            config={},
            origin_kind="catalog",
            origin_catalog_key=catalog_key,
            status="healthy",
        )
        custom_source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            kind="rss",
            name="custom source",
            enabled=True,
            config={},
            origin_kind="custom",
            origin_catalog_key=None,
            status="healthy",
        )
        session.add_all([catalog_source, custom_source])
        await session.commit()

        await session.execute(BOOTSTRAP_SQL)
        await session.commit()

        catalog_rec = (
            await session.execute(
                select(SourceCredibilityRecord).where(
                    SourceCredibilityRecord.source_id == catalog_source.id
                )
            )
        ).scalars().one()
        custom_rec = (
            await session.execute(
                select(SourceCredibilityRecord).where(
                    SourceCredibilityRecord.source_id == custom_source.id
                )
            )
        ).scalars().one()

        # 75 / 100 == 0.75 (NOT 0 — the ::float cast is load-bearing).
        assert catalog_rec.accuracy_rate == pytest.approx(0.75)
        # No catalog match → COALESCE(NULL, 50) / 100 == neutral prior 0.5.
        assert custom_rec.accuracy_rate == pytest.approx(0.5)
        # Counters start clean; accuracy is the only thing bootstrapped.
        assert catalog_rec.total_claim_count == 0
        assert custom_rec.verified_claim_count == 0
