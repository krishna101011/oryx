"""Phase 6 Wave B (UI) — Notification Preferences + Automation Hub backend surface.

Covers the resolved-defaults extension of GET /v1/activity/alerts/preferences
(docs/PHASE_6_ARCHITECTURE.md §5: backfill missing category/channel
combinations server-side), the PUT round-trip the preferences screen drives,
and the NEW GET /v1/automation-log transparency feed (automation_log +
digest_runs merged, account-scoped, reverse-chronological).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db

CATEGORIES = ("security", "system", "verification", "publishing")
CHANNELS = ("in_app", "push", "email")


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> dict:
    """Sign a fresh account up; return access token + account/workspace ids."""
    signup = await client.post("/v1/auth/signup", json={
        "email": f"hub+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "Hub",
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


# -------------------- alerts/preferences --------------------


@pytest.mark.asyncio
async def test_alert_preferences_get_returns_resolved_grid(app) -> None:
    """A brand-new account with NO stored rows gets the complete backfilled
    grid: 4 categories x 3 channels at the shared default 'instant' — and no
    cadence-label types (instant_alert/daily_digest/weekly_digest) appear."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        res = await client.get("/v1/activity/alerts/preferences", headers=ids["headers"])
        assert res.status_code == 200
        grid = res.json()["data"]
        assert len(grid) == 12
        combos = {(p["type"], p["channel"]) for p in grid}
        assert combos == {(c, ch) for c in CATEGORIES for ch in CHANNELS}
        assert all(p["frequency"] == "instant" for p in grid)
        assert all(p["quietHours"] is None for p in grid)


@pytest.mark.asyncio
async def test_alert_preferences_put_then_get_roundtrip(app) -> None:
    """The screen's write path: PUT verification/in_app to 'daily', then GET —
    exactly that cell changed, the other 11 stay at the resolved default."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        put = await client.put(
            "/v1/activity/alerts/preferences/verification/in_app",
            json={"frequency": "daily"},
            headers=ids["headers"],
        )
        assert put.status_code == 200
        assert put.json()["data"]["frequency"] == "daily"

        grid = (
            await client.get("/v1/activity/alerts/preferences", headers=ids["headers"])
        ).json()["data"]
        by_combo = {(p["type"], p["channel"]): p["frequency"] for p in grid}
        assert by_combo[("verification", "in_app")] == "daily"
        others = [f for k, f in by_combo.items() if k != ("verification", "in_app")]
        assert len(others) == 11
        assert all(f == "instant" for f in others)


@pytest.mark.asyncio
async def test_alert_preferences_rejects_unauthenticated(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get("/v1/activity/alerts/preferences")
        assert res.status_code == 401
        res = await client.put(
            "/v1/activity/alerts/preferences/system/in_app", json={"frequency": "off"}
        )
        assert res.status_code == 401


# -------------------- automation-log --------------------


async def _seed_dispatch_row(
    sm, *, account_id, workspace_id, created_at,
    action: str = "suppressed_by_preference", channel: str = "in_app",
    detail: str | None = None,
) -> uuid.UUID:
    from oryx.core.models import AutomationLog

    row_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            AutomationLog(
                id=row_id,
                account_id=account_id,
                workspace_id=workspace_id,
                activity_inbox_id=None,
                triggered_by_event_type="content.published",
                triggered_by_event_id=uuid.uuid4(),
                action_taken=action,
                channel=channel,
                detail=detail,
                created_at=created_at,
            )
        )
        await session.commit()
    return row_id


async def _seed_digest_row(sm, *, account_id, sent_at) -> uuid.UUID:
    from oryx.core.models import DigestRun

    row_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            DigestRun(
                id=row_id,
                account_id=account_id,
                activity_type="publishing",
                frequency="daily",
                window_start=sent_at - timedelta(days=1),
                window_end=sent_at,
                sent_at=sent_at,
            )
        )
        await session.commit()
    return row_id


@pytest.mark.asyncio
async def test_automation_log_merges_dispatch_and_digest_entries(app, sm) -> None:
    """One automation_log row and one later digest_runs row: the feed returns
    both, newest first, each with its kind-specific fields mapped."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        t0 = datetime(2026, 7, 6, 10, 0, tzinfo=UTC)
        dispatch_id = await _seed_dispatch_row(
            sm, account_id=ids["account_id"], workspace_id=ids["workspace_id"],
            created_at=t0,
        )
        digest_id = await _seed_digest_row(
            sm, account_id=ids["account_id"], sent_at=t0 + timedelta(hours=2)
        )

        res = await client.get("/v1/automation-log", headers=ids["headers"])
        assert res.status_code == 200
        entries = res.json()["data"]["entries"]
        assert [e["id"] for e in entries] == [str(digest_id), str(dispatch_id)]

        digest, dispatch = entries
        assert digest["kind"] == "digest"
        assert digest["action"] == "digest_sent"
        assert digest["category"] == "publishing"
        assert digest["frequency"] == "daily"
        assert digest["windowEnd"] is not None
        assert dispatch["kind"] == "dispatch"
        assert dispatch["action"] == "suppressed_by_preference"
        assert dispatch["eventType"] == "content.published"
        assert dispatch["category"] is None
        assert dispatch["activityInboxId"] is None


@pytest.mark.asyncio
async def test_automation_log_exposes_channel_and_failure_detail(app, sm) -> None:
    """The Automation Hub detail view's data (migration 0024): a push_failed
    row surfaces its channel AND the persisted failure reason; digest entries
    carry null for both (digest_runs has neither)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        t0 = datetime(2026, 7, 11, 9, 0, tzinfo=UTC)
        failed_id = await _seed_dispatch_row(
            sm, account_id=ids["account_id"], workspace_id=ids["workspace_id"],
            created_at=t0, action="push_failed", channel="push",
            detail="no_registered_device",
        )
        digest_id = await _seed_digest_row(
            sm, account_id=ids["account_id"], sent_at=t0 + timedelta(hours=1)
        )

        entries = (
            await client.get("/v1/automation-log", headers=ids["headers"])
        ).json()["data"]["entries"]
        by_id = {e["id"]: e for e in entries}

        failed = by_id[str(failed_id)]
        assert failed["action"] == "push_failed"
        assert failed["channel"] == "push"
        assert failed["detail"] == "no_registered_device"

        digest = by_id[str(digest_id)]
        assert digest["channel"] is None
        assert digest["detail"] is None


@pytest.mark.asyncio
async def test_automation_log_pre_capture_failed_row_has_null_detail(app, sm) -> None:
    """Rows recorded before reason capture keep detail=null (no backfill, no
    invented reason) — the client copy states that honestly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        legacy_id = await _seed_dispatch_row(
            sm, account_id=ids["account_id"], workspace_id=ids["workspace_id"],
            created_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
            action="push_failed", channel="push", detail=None,
        )
        entries = (
            await client.get("/v1/automation-log", headers=ids["headers"])
        ).json()["data"]["entries"]
        legacy = {e["id"]: e for e in entries}[str(legacy_id)]
        assert legacy["action"] == "push_failed"
        assert legacy["detail"] is None


@pytest.mark.asyncio
async def test_automation_log_scoped_to_own_account(app, sm) -> None:
    """Account A's feed never contains rows seeded for account B."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        a = await _signup(client)
        b = await _signup(client)
        b_row = await _seed_dispatch_row(
            sm, account_id=b["account_id"], workspace_id=b["workspace_id"],
            created_at=datetime.now(UTC),
        )

        a_entries = (
            await client.get("/v1/automation-log", headers=a["headers"])
        ).json()["data"]["entries"]
        assert str(b_row) not in [e["id"] for e in a_entries]
        assert a_entries == []  # fresh account, nothing dispatched for it


@pytest.mark.asyncio
async def test_automation_log_rejects_unauthenticated(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get("/v1/automation-log")
        assert res.status_code == 401


# -------------------- Wave A drift regression --------------------


@pytest.mark.asyncio
async def test_activity_inbox_serializes_phase6_categories(app, sm) -> None:
    """Regression: Wave A widened the activity_type DB enum ('verification'/
    'publishing') but not the shared-types ActivityType literal — so a
    dispatched row crashed GET /activity/inbox serialization until this wave
    widened the mirror. Prove a 'verification' row round-trips."""
    from oryx.core.models import ActivityInbox

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        row_id = uuid.uuid4()
        async with sm() as session:
            session.add(
                ActivityInbox(
                    id=row_id, account_id=ids["account_id"],
                    workspace_id=ids["workspace_id"], type="verification",
                    severity="warning", title="Conflict detected", body=None,
                    data={},
                )
            )
            await session.commit()

        res = await client.get("/v1/activity/inbox", headers=ids["headers"])
        assert res.status_code == 200
        items = res.json()["data"]["items"]
        mine = [i for i in items if i["id"] == str(row_id)]
        assert len(mine) == 1
        assert mine[0]["type"] == "verification"


# -------------------- feature flag --------------------


@pytest.mark.asyncio
async def test_ff_automation_enabled_by_default(app) -> None:
    """Migration 0016 flips ff_automation's global default ON — the Automation
    Hub depends only on shipped Wave A/B reads, not Wave C push. Migration 0018
    (Wave C) then flips ff_push_delivery ON too: the flag now pins TRUE — this
    assertion was deliberately updated from False when Wave C shipped the push
    path (client registration stays guarded on dev builds; server delivery
    stays log-only until PUSH_PROVIDER=real is configured)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        ids = await _signup(client)
        flags = (
            await client.get("/v1/feature-flags", headers=ids["headers"])
        ).json()["data"]
        assert flags["ff_automation"] is True
        assert flags["ff_push_delivery"] is True  # Wave C shipped; pinned ON
