"""Phase 8 Wave A — authoring endpoints + certificate issuance, end to end
against real Postgres (docs/PHASE_8_TRAINING_ARCHITECTURE.md §2/§4).

Covers: the is_platform_admin gate rejects a real workspace owner/admin
(proving the corrected §4 boundary — a workspace role is NOT enough, only
the account-level flag is), a platform admin's real Course/Module/Lesson
CRUD roundtrip, Certificate.issue_if_eligible's real "all lessons complete"
rule, and the video-upload-url endpoint's honest 503 when no Cloudflare
credentials are configured.
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

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
    """Returns (access_token, email). Signup makes this account the OWNER
    of its own real personal workspace — the highest workspace role that
    exists — deliberately, so denial tests prove the corrected §4
    boundary against the strongest workspace role, not a weak one."""
    email = f"training+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Training Test",
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
async def test_workspace_owner_without_platform_flag_is_denied_course_authoring(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, _ = await _signup(client)
        res = await client.post(
            "/v1/training/courses",
            json={"title": "Should be denied"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_platform_admin_full_course_module_lesson_crud_roundtrip(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/v1/training/courses",
            json={"title": "Foundations", "description": "Intro course"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        course = res.json()["data"]
        assert course["title"] == "Foundations"
        assert "workspaceId" not in course
        course_id = course["id"]

        res = await client.get("/v1/training/courses", headers=headers)
        assert res.status_code == 200
        assert any(c["id"] == course_id for c in res.json()["data"])

        res = await client.get(f"/v1/training/courses/{course_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["data"]["id"] == course_id

        res = await client.patch(
            f"/v1/training/courses/{course_id}",
            json={"title": "Foundations (updated)"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["title"] == "Foundations (updated)"
        assert res.json()["data"]["description"] == "Intro course"

        res = await client.post(
            f"/v1/training/courses/{course_id}/modules",
            json={"title": "Module 1", "order": 1},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        module = res.json()["data"]
        assert module["courseId"] == course_id
        module_id = module["id"]

        res = await client.get(f"/v1/training/courses/{course_id}/modules", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1

        res = await client.post(
            f"/v1/training/modules/{module_id}/lessons",
            json={"title": "Lesson 1", "order": 1},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        lesson = res.json()["data"]
        assert lesson["moduleId"] == module_id
        assert lesson["videoAssetId"] is None
        lesson_id = lesson["id"]

        res = await client.get(f"/v1/training/modules/{module_id}/lessons", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1

        res = await client.patch(
            f"/v1/training/lessons/{lesson_id}",
            json={"video_asset_id": "cf-stream-uid-123"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["data"]["videoAssetId"] == "cf-stream-uid-123"

        res = await client.delete(f"/v1/training/lessons/{lesson_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["data"]["deleted"] is True

        res = await client.get(f"/v1/training/modules/{module_id}/lessons", headers=headers)
        assert res.json()["data"] == []


@pytest.mark.asyncio
async def test_module_and_lesson_creation_404_on_unknown_parent(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            f"/v1/training/courses/{uuid.uuid4()}/modules",
            json={"title": "Orphan module"},
            headers=headers,
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

        res = await client.post(
            f"/v1/training/modules/{uuid.uuid4()}/lessons",
            json={"title": "Orphan lesson"},
            headers=headers,
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_certificate_only_issued_once_every_lesson_is_complete(sm) -> None:
    from oryx.core.models import Account, Course, Lesson, Module
    from oryx.services.training.repository import CertificateRepository, LessonProgressRepository

    now = datetime.now(UTC)
    async with sm() as session:
        learner = Account(
            id=uuid.uuid4(),
            email=f"learner+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        author = Account(
            id=uuid.uuid4(),
            email=f"author+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
            is_platform_admin=True,
        )
        session.add_all([learner, author])
        await session.flush()
        course = Course(id=uuid.uuid4(), title="Cert Course", created_by=author.id)
        session.add(course)
        await session.flush()
        module = Module(id=uuid.uuid4(), course_id=course.id, title="M1", order=0)
        session.add(module)
        await session.flush()
        lesson_1 = Lesson(id=uuid.uuid4(), module_id=module.id, title="L1", order=0)
        lesson_2 = Lesson(id=uuid.uuid4(), module_id=module.id, title="L2", order=1)
        session.add_all([lesson_1, lesson_2])
        await session.commit()
        account_id, course_id = learner.id, course.id
        lesson_1_id, lesson_2_id = lesson_1.id, lesson_2.id

    async with sm() as session:
        result = await CertificateRepository(session).issue_if_eligible(
            account_id=account_id, course_id=course_id
        )
        assert result is None, "must not issue with zero lessons completed"

    async with sm() as session:
        await LessonProgressRepository(session).mark_complete(
            account_id=account_id, lesson_id=lesson_1_id
        )
        await session.commit()

    async with sm() as session:
        result = await CertificateRepository(session).issue_if_eligible(
            account_id=account_id, course_id=course_id
        )
        assert result is None, "must not issue with only 1 of 2 lessons completed"

    async with sm() as session:
        await LessonProgressRepository(session).mark_complete(
            account_id=account_id, lesson_id=lesson_2_id
        )
        await session.commit()

    async with sm() as session:
        issued = await CertificateRepository(session).issue_if_eligible(
            account_id=account_id, course_id=course_id
        )
        assert issued is not None
        await session.commit()
        issued_account_id, issued_course_id = issued.account_id, issued.course_id

    async with sm() as session:
        same = await CertificateRepository(session).issue_if_eligible(
            account_id=account_id, course_id=course_id
        )
        assert same is not None
        assert same.account_id == issued_account_id
        assert same.course_id == issued_course_id


@pytest.mark.asyncio
async def test_video_upload_url_is_honestly_unavailable_without_cloudflare_credentials(
    app, sm
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, email = await _signup(client)
        await _promote_to_platform_admin(sm, email)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/v1/training/courses", json={"title": "Video Course"}, headers=headers
        )
        course_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/courses/{course_id}/modules", json={"title": "M1"}, headers=headers
        )
        module_id = res.json()["data"]["id"]
        res = await client.post(
            f"/v1/training/modules/{module_id}/lessons", json={"title": "L1"}, headers=headers
        )
        lesson_id = res.json()["data"]["id"]

        res = await client.post(
            f"/v1/training/lessons/{lesson_id}/video-upload-url", headers=headers
        )
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "VIDEO_PROVIDER_UNAVAILABLE"
