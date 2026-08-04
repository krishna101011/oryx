"""Phase 8 Wave C — the two new learner-facing endpoints the mobile
course-list and lesson-viewer screens actually call, end to end against
real Postgres.

Covers: GET /training/catalog lists every real course with THIS account's
real per-course enrollment status (distinct from the admin-only
GET /training/courses); GET /training/lessons/{id} returns real title +
transcript + a derived hasVideo boolean and NEVER the raw video_asset_id
string (recon found no endpoint anywhere resolves that placeholder into
real Cloudflare playback data — exposing it to a learner would be actively
misleading); both require authentication, no workspace/platform-admin
requirement.
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _signup(client: AsyncClient) -> tuple[str, str]:
    email = f"catalog+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Catalog Test",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "Pytest Device",
            "devicePlatform": "ios",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["tokens"]["accessToken"], email


async def _promote_to_platform_admin(sm, email: str) -> None:
    from oryx.core.models import Account

    async with sm() as session:
        account = (
            await session.execute(select(Account).where(Account.email == email))
        ).scalar_one()
        account.is_platform_admin = True
        await session.commit()


@pytest.mark.asyncio
async def test_catalog_requires_authentication(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get("/v1/training/catalog")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_lesson_detail_requires_authentication(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get(f"/v1/training/lessons/{uuid.uuid4()}")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_catalog_lists_real_courses_with_real_per_course_enrollment_status(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        res = await client.post(
            "/v1/training/courses",
            json={"title": "Catalog Course A", "description": "First"},
            headers=admin_headers,
        )
        course_a = res.json()["data"]["id"]
        res = await client.post(
            "/v1/training/courses", json={"title": "Catalog Course B"}, headers=admin_headers
        )
        course_b = res.json()["data"]["id"]

        learner_token, _ = await _signup(client)
        learner_headers = {"Authorization": f"Bearer {learner_token}"}

        res = await client.get("/v1/training/catalog", headers=learner_headers)
        assert res.status_code == 200, res.text
        by_id = {c["id"]: c for c in res.json()["data"]["courses"]}
        assert by_id[course_a]["enrolled"] is False
        assert by_id[course_a]["enrolledAt"] is None
        assert by_id[course_b]["enrolled"] is False

        await client.post(f"/v1/training/courses/{course_a}/enroll", headers=learner_headers)

        res = await client.get("/v1/training/catalog", headers=learner_headers)
        by_id = {c["id"]: c for c in res.json()["data"]["courses"]}
        assert by_id[course_a]["enrolled"] is True
        assert by_id[course_a]["enrolledAt"] is not None
        assert by_id[course_b]["enrolled"] is False, "enrolling in A must not mark B enrolled"


@pytest.mark.asyncio
async def test_lesson_detail_returns_transcript_and_has_video_never_raw_asset_id(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        res = await client.post(
            "/v1/training/courses", json={"title": "Video Lesson Course"}, headers=admin_headers
        )
        course_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/courses/{course_id}/modules", json={"title": "M1"}, headers=admin_headers
        )
        module_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/modules/{module_id}/lessons",
            json={
                "title": "Conflict detection workflow",
                "transcript_text": "When two trusted sources disagree...",
                "video_asset_id": "cf-stream-uid-placeholder",
            },
            headers=admin_headers,
        )
        lesson_id = res.json()["data"]["id"]

        learner_token, _ = await _signup(client)
        res = await client.get(
            f"/v1/training/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
    assert res.status_code == 200, res.text
    lesson = res.json()["data"]
    assert lesson["title"] == "Conflict detection workflow"
    assert lesson["transcriptText"] == "When two trusted sources disagree..."
    assert lesson["hasVideo"] is True
    assert lesson["courseId"] == course_id
    assert "videoAssetId" not in lesson, "raw video_asset_id must never reach a learner"
    assert "cf-stream-uid-placeholder" not in res.text, (
        "the raw placeholder string must not leak anywhere in the response"
    )


@pytest.mark.asyncio
async def test_lesson_detail_has_video_false_and_reflects_real_completion_state(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        res = await client.post(
            "/v1/training/courses", json={"title": "No Video Course"}, headers=admin_headers
        )
        course_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/courses/{course_id}/modules", json={"title": "M1"}, headers=admin_headers
        )
        module_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/modules/{module_id}/lessons",
            json={"title": "Text-only lesson"},
            headers=admin_headers,
        )
        lesson_id = res.json()["data"]["id"]

        learner_token, _ = await _signup(client)
        learner_headers = {"Authorization": f"Bearer {learner_token}"}

        res = await client.get(f"/v1/training/lessons/{lesson_id}", headers=learner_headers)
        lesson = res.json()["data"]
        assert lesson["hasVideo"] is False
        assert lesson["completed"] is False
        assert lesson["completedAt"] is None

        await client.post(f"/v1/training/lessons/{lesson_id}/complete", headers=learner_headers)

        res = await client.get(f"/v1/training/lessons/{lesson_id}", headers=learner_headers)
        lesson = res.json()["data"]
        assert lesson["completed"] is True
        assert lesson["completedAt"] is not None
