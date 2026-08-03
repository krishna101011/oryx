"""Phase 8 Wave B — learner-facing enroll/complete/progress, end to end
against real Postgres.

Covers: the Wave A idempotency gap (EnrollmentRepository.enroll and
LessonProgressRepository.mark_complete both used to do an unconditional
insert with no existence check — a second call would IntegrityError on
the composite PK) is genuinely fixed, proven by a real double-call through
the HTTP endpoints, not just reasoned about; completing the final lesson
via the real endpoint auto-issues a real certificate in the SAME request
(tying this endpoint to CertificateRepository.issue_if_eligible's
already-proven Wave A logic); an unauthenticated request is rejected; and
any real signed-in account succeeds with no workspace/platform-admin
requirement — the corrected §4 reasoning one level down from authoring.
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
    email = f"learner+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Learner Test",
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


async def _seed_course_with_lessons(client: AsyncClient, admin_headers: dict, *, lesson_count: int):
    """Real authoring calls through the real Wave A endpoints — no direct
    DB seeding, so this test exercises the same path a real admin would."""
    res = await client.post(
        "/v1/training/courses", json={"title": "Learner Course"}, headers=admin_headers
    )
    course_id = res.json()["data"]["id"]
    res = await client.post(
        f"/v1/training/courses/{course_id}/modules", json={"title": "M1"}, headers=admin_headers
    )
    module_id = res.json()["data"]["id"]
    lesson_ids = []
    for i in range(lesson_count):
        res = await client.post(
            f"/v1/training/modules/{module_id}/lessons",
            json={"title": f"L{i + 1}", "order": i},
            headers=admin_headers,
        )
        lesson_ids.append(res.json()["data"]["id"])
    return course_id, lesson_ids


@pytest.mark.asyncio
async def test_unauthenticated_enroll_is_rejected(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.post(f"/v1/training/courses/{uuid.uuid4()}/enroll")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_any_signed_in_account_can_enroll_no_platform_admin_needed(app, sm) -> None:
    """The corrected reasoning one level down from authoring: a plain
    workspace owner (the default, non-admin state of a fresh signup) must
    succeed here, unlike the authoring endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        course_id, _ = await _seed_course_with_lessons(
            client, {"Authorization": f"Bearer {admin_token}"}, lesson_count=1
        )

        learner_token, _ = await _signup(client)
        res = await client.post(
            f"/v1/training/courses/{course_id}/enroll",
            headers={"Authorization": f"Bearer {learner_token}"},
        )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["courseId"] == course_id


@pytest.mark.asyncio
async def test_double_enroll_returns_the_same_row_cleanly_no_integrity_error(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        course_id, _ = await _seed_course_with_lessons(
            client, {"Authorization": f"Bearer {admin_token}"}, lesson_count=1
        )

        learner_token, _ = await _signup(client)
        headers = {"Authorization": f"Bearer {learner_token}"}

        first = await client.post(f"/v1/training/courses/{course_id}/enroll", headers=headers)
        assert first.status_code == 200, first.text

        second = await client.post(f"/v1/training/courses/{course_id}/enroll", headers=headers)
        assert second.status_code == 200, second.text
        assert second.json()["data"]["enrolledAt"] == first.json()["data"]["enrolledAt"]


@pytest.mark.asyncio
async def test_double_complete_returns_the_same_row_cleanly_no_integrity_error(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        _, lesson_ids = await _seed_course_with_lessons(
            client, {"Authorization": f"Bearer {admin_token}"}, lesson_count=2
        )
        lesson_id = lesson_ids[0]

        learner_token, _ = await _signup(client)
        headers = {"Authorization": f"Bearer {learner_token}"}

        first = await client.post(f"/v1/training/lessons/{lesson_id}/complete", headers=headers)
        assert first.status_code == 200, first.text

        second = await client.post(f"/v1/training/lessons/{lesson_id}/complete", headers=headers)
        assert second.status_code == 200, second.text
        assert (
            second.json()["data"]["lessonProgress"]["completedAt"]
            == first.json()["data"]["lessonProgress"]["completedAt"]
        )


@pytest.mark.asyncio
async def test_completing_final_lesson_auto_issues_certificate_same_request(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        course_id, lesson_ids = await _seed_course_with_lessons(
            client, {"Authorization": f"Bearer {admin_token}"}, lesson_count=2
        )

        learner_token, _ = await _signup(client)
        headers = {"Authorization": f"Bearer {learner_token}"}

        res = await client.post(
            f"/v1/training/lessons/{lesson_ids[0]}/complete", headers=headers
        )
        assert res.status_code == 200, res.text
        assert res.json()["data"]["certificate"] is None, (
            "must not issue a certificate with only 1 of 2 lessons complete"
        )

        res = await client.post(
            f"/v1/training/lessons/{lesson_ids[1]}/complete", headers=headers
        )
        assert res.status_code == 200, res.text
        certificate = res.json()["data"]["certificate"]
        assert certificate is not None, (
            "completing the FINAL lesson must auto-issue a certificate in this same request"
        )
        assert certificate["courseId"] == course_id

        res = await client.get(f"/v1/training/courses/{course_id}/progress", headers=headers)
        assert res.status_code == 200
        progress = res.json()["data"]
        assert progress["certificate"] is not None
        assert all(lesson["completed"] for lesson in progress["lessons"])


@pytest.mark.asyncio
async def test_progress_endpoint_reports_real_enrollment_and_per_lesson_state(app, sm) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        admin_token, admin_email = await _signup(client)
        await _promote_to_platform_admin(sm, admin_email)
        course_id, lesson_ids = await _seed_course_with_lessons(
            client, {"Authorization": f"Bearer {admin_token}"}, lesson_count=2
        )

        learner_token, _ = await _signup(client)
        headers = {"Authorization": f"Bearer {learner_token}"}

        res = await client.get(f"/v1/training/courses/{course_id}/progress", headers=headers)
        assert res.status_code == 200
        progress = res.json()["data"]
        assert progress["enrollment"] is None
        assert len(progress["lessons"]) == 2
        assert all(not lesson["completed"] for lesson in progress["lessons"])
        assert progress["certificate"] is None

        await client.post(f"/v1/training/courses/{course_id}/enroll", headers=headers)
        await client.post(f"/v1/training/lessons/{lesson_ids[0]}/complete", headers=headers)

        res = await client.get(f"/v1/training/courses/{course_id}/progress", headers=headers)
        progress = res.json()["data"]
        assert progress["enrollment"] is not None
        completed = {l["lessonId"]: l["completed"] for l in progress["lessons"]}
        assert completed[lesson_ids[0]] is True
        assert completed[lesson_ids[1]] is False
