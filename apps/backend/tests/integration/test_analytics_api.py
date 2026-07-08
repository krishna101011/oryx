"""Phase 7 Wave B — the dashboard's two read contracts.

GET /v1/analytics/rollups (workspace-scoped daily series, read ONLY from
analytics_rollups_daily) and GET /v1/analytics/publishing (§3.4: success rate
from the same rollups + the one sanctioned direct time-to-publish query).

Covers the Wave B mandatory scenarios: seeded-series correctness, cross-
workspace isolation, the near-empty-history case (the REAL state of every
workspace today — Wave A only just shipped and dev has zero rollup rows), the
time-to-publish computation against seeded draft/publication timestamp pairs,
and the engagement-absence proof (§3.4 demoted engagement explicitly; the
response shape must not quietly grow one).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> dict:
    signup = await client.post("/v1/auth/signup", json={
        "email": f"analytics+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "Ana",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    headers = {"Authorization": f"Bearer {access}"}
    me = (await client.get("/v1/auth/me", headers=headers)).json()["data"]
    return {
        "headers": headers,
        "account_id": uuid.UUID(me["account"]["id"]),
        "workspace_id": uuid.UUID(me["workspace"]["id"]),
    }


async def _seed_rollup(sm, *, workspace_id, metric_key, day, value) -> None:
    from oryx.core.models import AnalyticsRollupDaily

    async with sm() as session:
        session.add(
            AnalyticsRollupDaily(
                id=uuid.uuid4(), workspace_id=workspace_id,
                metric_key=metric_key, date=day, value=value,
            )
        )
        await session.commit()


async def _seed_published_pair(
    sm, *, workspace_id, account_id, created_at, published_at
) -> None:
    """One content_drafts + delivered publications pair with controlled
    timestamps — the unit time-to-publish is computed over. Walks the real FK
    chain (research workspace -> packet -> draft -> target -> publication),
    same shape as test_calendar_scheduler's seed helpers."""
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import (
        ContentDraft,
        Publication,
        PublishTarget,
        ResearchPacket,
        ResearchWorkspace,
    )

    ct, iv = encrypt_credentials({"secret": "s"})
    async with sm() as session:
        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account_id, workspace_id=workspace_id,
            name="RW",
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(), research_workspace_id=rws.id,
            workspace_id=workspace_id, name="P", status="consumed",
            intelligence_object_ids=[], conflict_acknowledged_ids=[],
            ready_at=created_at,
        )
        session.add(packet)
        await session.flush()
        draft = ContentDraft(
            id=uuid.uuid4(), workspace_id=workspace_id, account_id=account_id,
            packet_id=packet.id, format="article", title="Timed Draft",
            status="published", current_version=1,
            generation_model="claude-sonnet-4-6", generation_version=1,
            created_at=created_at, published_at=published_at,
        )
        session.add(draft)
        await session.flush()
        target = PublishTarget(
            id=uuid.uuid4(), workspace_id=workspace_id, name="T",
            channel="webhook", credentials=ct, credentials_iv=iv,
            config={}, is_active=True,
        )
        session.add(target)
        await session.flush()
        session.add(
            Publication(
                id=uuid.uuid4(), draft_id=draft.id, version_number=1,
                target_id=target.id, workspace_id=workspace_id,
                status="delivered", attempt_count=1,
                published_at=published_at,
            )
        )
        await session.commit()


# -------------------- rollups --------------------


@pytest.mark.asyncio
async def test_rollups_endpoint_returns_seeded_series(app, sm) -> None:
    """Mandatory scenario 1: seeded rows come back as per-metric ascending
    daily series, and a row outside the requested range is excluded — the
    date-range params actually filter."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        ws = ids["workspace_id"]
        await _seed_rollup(sm, workspace_id=ws, metric_key="claims_verified",
                           day=date(2026, 7, 6), value=4)
        await _seed_rollup(sm, workspace_id=ws, metric_key="claims_verified",
                           day=date(2026, 7, 7), value=7)
        await _seed_rollup(sm, workspace_id=ws, metric_key="drafts_published",
                           day=date(2026, 7, 7), value=2)
        # Outside the requested range — must not appear.
        await _seed_rollup(sm, workspace_id=ws, metric_key="claims_verified",
                           day=date(2026, 6, 1), value=99)

        res = await client.get(
            "/v1/analytics/rollups?from=2026-07-01&to=2026-07-08",
            headers=ids["headers"],
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["from"] == "2026-07-01"
        assert data["to"] == "2026-07-08"
        assert data["series"]["claims_verified"] == [
            {"date": "2026-07-06", "value": 4},
            {"date": "2026-07-07", "value": 7},
        ]
        assert data["series"]["drafts_published"] == [
            {"date": "2026-07-07", "value": 2},
        ]


@pytest.mark.asyncio
async def test_rollups_endpoint_is_workspace_isolated(app, sm) -> None:
    """Mandatory scenario 2: workspace A never sees workspace B's rollups on
    either endpoint — the series stay separate and B's delivered publication
    does not leak into A's time-to-publish sample."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        a = await _signup(client)
        b = await _signup(client)
        day = date(2026, 7, 7)
        await _seed_rollup(sm, workspace_id=a["workspace_id"],
                           metric_key="intake_items_received", day=day, value=1)
        await _seed_rollup(sm, workspace_id=b["workspace_id"],
                           metric_key="intake_items_received", day=day, value=50)
        await _seed_rollup(sm, workspace_id=b["workspace_id"],
                           metric_key="claims_verified", day=day, value=9)
        t0 = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
        await _seed_published_pair(
            sm, workspace_id=b["workspace_id"], account_id=b["account_id"],
            created_at=t0, published_at=t0 + timedelta(hours=1),
        )

        a_data = (
            await client.get(
                "/v1/analytics/rollups?from=2026-07-01&to=2026-07-08",
                headers=a["headers"],
            )
        ).json()["data"]
        assert a_data["series"] == {
            "intake_items_received": [{"date": "2026-07-07", "value": 1}]
        }

        a_pub = (
            await client.get("/v1/analytics/publishing", headers=a["headers"])
        ).json()["data"]
        assert a_pub["timeToPublish"]["sampleSize"] == 0


@pytest.mark.asyncio
async def test_rollups_near_empty_history_returns_cleanly(app) -> None:
    """Mandatory scenario 3 (backend half): a brand-new workspace — the REAL
    state of every workspace today, dev's rollup table is empty — gets a clean
    200 with an empty series map and a null-rate/empty publishing view, never
    an error. The UI's still-gathering state builds on exactly this shape
    (frontend half: presenter.test.ts)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)

        rollups = await client.get("/v1/analytics/rollups", headers=ids["headers"])
        assert rollups.status_code == 200
        assert rollups.json()["data"]["series"] == {}

        pub = await client.get("/v1/analytics/publishing", headers=ids["headers"])
        assert pub.status_code == 200
        data = pub.json()["data"]
        assert data["success"] == {"published": 0, "failed": 0, "successRate": None}
        assert data["timeToPublish"] == {
            "averageSeconds": None, "medianSeconds": None, "sampleSize": 0,
        }


# -------------------- publishing --------------------


@pytest.mark.asyncio
async def test_time_to_publish_computes_avg_and_median_from_seeded_pairs(
    app, sm
) -> None:
    """Mandatory scenario 4: three draft/publication pairs with known gaps
    (100s, 200s, 1000s) -> average 433.33s, median 200s, sample 3. The odd
    outlier is exactly why the median is served alongside the average."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        t0 = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
        for gap_seconds in (100, 200, 1000):
            await _seed_published_pair(
                sm, workspace_id=ids["workspace_id"],
                account_id=ids["account_id"], created_at=t0,
                published_at=t0 + timedelta(seconds=gap_seconds),
            )

        data = (
            await client.get("/v1/analytics/publishing", headers=ids["headers"])
        ).json()["data"]
        ttp = data["timeToPublish"]
        assert ttp["sampleSize"] == 3
        assert ttp["medianSeconds"] == 200.0
        assert abs(ttp["averageSeconds"] - (100 + 200 + 1000) / 3) < 0.01


@pytest.mark.asyncio
async def test_publishing_success_rate_sums_rollups(app, sm) -> None:
    """The §3.4 numerator/denominator: drafts_published vs publish_failures
    summed over the window from the rollups — 8 published, 2 failed -> 0.8."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        ws = ids["workspace_id"]
        await _seed_rollup(sm, workspace_id=ws, metric_key="drafts_published",
                           day=date(2026, 7, 6), value=5)
        await _seed_rollup(sm, workspace_id=ws, metric_key="drafts_published",
                           day=date(2026, 7, 7), value=3)
        await _seed_rollup(sm, workspace_id=ws, metric_key="publish_failures",
                           day=date(2026, 7, 7), value=2)

        data = (
            await client.get(
                "/v1/analytics/publishing?from=2026-07-01&to=2026-07-08",
                headers=ids["headers"],
            )
        ).json()["data"]
        assert data["success"] == {
            "published": 8, "failed": 2, "successRate": 0.8,
        }


def _all_keys(node) -> set[str]:
    """Every key at every depth of a JSON payload."""
    keys: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            keys |= _all_keys(v)
    elif isinstance(node, list):
        for item in node:
            keys |= _all_keys(item)
    return keys


@pytest.mark.asyncio
async def test_publishing_response_contains_no_engagement_fields(app, sm) -> None:
    """Mandatory scenario 5: prove the ABSENCE. §3.4 demoted the engagement
    view because no real signal exists — the publishing response's key set is
    exactly the documented delivery-performance shape and contains no
    engagement-flavoured key at any depth, even with real data present."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        await _seed_rollup(sm, workspace_id=ids["workspace_id"],
                           metric_key="drafts_published", day=date(2026, 7, 7),
                           value=3)
        t0 = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
        await _seed_published_pair(
            sm, workspace_id=ids["workspace_id"], account_id=ids["account_id"],
            created_at=t0, published_at=t0 + timedelta(minutes=5),
        )

        data = (
            await client.get("/v1/analytics/publishing", headers=ids["headers"])
        ).json()["data"]

        # The exact contract — nothing more.
        assert set(data.keys()) == {"success", "timeToPublish"}
        assert set(data["success"].keys()) == {"published", "failed", "successRate"}
        assert set(data["timeToPublish"].keys()) == {
            "averageSeconds", "medianSeconds", "sampleSize",
        }

        # And no engagement-flavoured key anywhere, at any depth.
        engagement_markers = (
            "view", "engagement", "impression", "click", "like", "share",
            "reach", "follower",
        )
        for key in _all_keys(data):
            lowered = key.lower()
            assert not any(marker in lowered for marker in engagement_markers), (
                f"engagement-flavoured key leaked into publishing view: {key}"
            )


@pytest.mark.asyncio
async def test_analytics_endpoints_reject_unauthenticated(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        assert (await client.get("/v1/analytics/rollups")).status_code == 401
        assert (await client.get("/v1/analytics/publishing")).status_code == 401


@pytest.mark.asyncio
async def test_ff_analytics_enabled_by_default(app) -> None:
    """Migration 0020 flips ff_analytics's global default ON — Wave B ships
    the whole read path the flag gates, and Phase 7 is purely observational
    (frozen doc §1.2), so the worst reachable state is the designed
    still-gathering dashboard."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        flags = (
            await client.get("/v1/feature-flags", headers=ids["headers"])
        ).json()["data"]
        assert flags["ff_analytics"] is True
