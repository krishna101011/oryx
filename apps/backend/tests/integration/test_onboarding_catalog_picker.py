"""Source-catalog picker rebuild (follow-up wave) — the real flow the new
mobile UI performs during onboarding: activate catalog entries for real via
origin_kind='catalog' POST /intake/sources as the user toggles tiles, then
submit the focus_sources onboarding step WITHOUT enabledSourceKeys (the field
the old flat picker used to send). This proves the WorkspaceSource-only path
is genuinely retired from this flow, not left as a silent no-op behind the
new UI: real activation lands in intake_sources, and workspace_sources stays
completely untouched for this workspace — not just unused by the new field,
but never written to at all.

Runs only when ORYX_TEST_DB is set (with migrations applied — 0027 seeds the
real Investing.com catalog rows this test activates).
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


async def _signup(client: AsyncClient) -> dict[str, str]:
    signup = await client.post("/v1/auth/signup", json={
        "email": f"catalogpicker+{uuid.uuid4().hex[:8]}@x.test",
        "password": "StrongPass123", "displayName": "CP",
        "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
    })
    access = signup.json()["data"]["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_onboarding_focus_sources_step_never_touches_workspace_sources_when_catalog_was_activated_for_real(
    app,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)

        # The real picker's onboarding defaults: activate two real catalog
        # entries via the real per-tile path (exactly what CatalogSourcePicker
        # + FocusAndSourcesScreen's provisioning effect do on mount).
        for key in ("coindesk", "investing_company_news"):
            res = await client.post("/v1/intake/sources", headers=headers, json={
                "name": "ignored", "kind": "manual",
                "origin_kind": "catalog", "origin_catalog_key": key,
                "config": {},
            })
            assert res.status_code == 200, res.text

        # Onboarding's focus_sources step, submitted the way the rebuilt
        # FocusAndSourcesScreen now does — NO enabledSourceKeys field at all.
        step = await client.post("/v1/onboarding/step", headers=headers, json={
            "step": "focus_sources", "focus": "both",
        })
        assert step.status_code == 200, step.text

        # Real activation landed for real.
        sources = await client.get("/v1/intake/sources", headers=headers)
        assert sources.status_code == 200, sources.text
        catalog_keys = {
            s["originCatalogKey"]
            for s in sources.json()["data"]
            if s["originKind"] == "catalog"
        }
        assert catalog_keys == {"coindesk", "investing_company_news"}

        # The dead path stayed dead: zero WorkspaceSource rows for this
        # workspace, not just zero rows for these two keys.
        workspace_sources = await client.get("/v1/sources/workspace", headers=headers)
        assert workspace_sources.status_code == 200, workspace_sources.text
        assert workspace_sources.json()["data"] == []


@pytest.mark.asyncio
async def test_onboarding_focus_sources_step_with_no_source_activity_still_leaves_workspace_sources_empty(
    app,
) -> None:
    """Regression floor: even a bare focus-only onboarding submission (no
    catalog activation at all that session) must not resurrect the old
    upsert-on-enabled_source_keys branch by any other route."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        headers = await _signup(client)

        step = await client.post("/v1/onboarding/step", headers=headers, json={
            "step": "focus_sources", "focus": "markets",
        })
        assert step.status_code == 200, step.text

        workspace_sources = await client.get("/v1/sources/workspace", headers=headers)
        assert workspace_sources.json()["data"] == []
