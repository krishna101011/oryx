"""Push delivery — Phase 6 Wave C coverage (dispatcher push step + devices API).

Drives NotificationDispatcher the same way test_notification_dispatcher.py
does (construct a DomainEvent, call the handler, assert on committed rows),
with FAKE push providers injected through the dispatcher's factory seam — the
real FCM/APNs wire protocol has its own unit coverage in
tests/unit/test_push_providers.py.

The mandatory Wave C scenarios covered here (quiet-hours pure-function cases
live in tests/unit/test_quiet_hours.py; client-side registration logic in
apps/mobile/src/lib/push/registration.test.ts):
  1. registration stores the token       test_device_registration_api_stores_token
  3. quiet window suppresses push        test_quiet_hours_inside_window_suppresses_push
  5. success logs push_sent              test_push_sent_logged_via_fake_provider
  6. provider failure logs push_failed   test_provider_failure_logs_push_failed_without_crashing
  7. no device token → push_failed       test_no_registered_device_logs_push_failed_with_reason
  8. inbox+log decoupled from push       test_inbox_and_log_survive_push_step_total_failure
  9. digest rows never push              test_digest_rows_do_not_trigger_push
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from oryx.services.activity.providers.push.base import (
    ProviderErrorKind,
    ProviderResult,
    PushMessage,
)

pytestmark = pytest.mark.requires_db

INTAKE_EVENT = "intake.item.received"  # category 'system'


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app
    return create_app()


class FakePushProvider:
    """Records every send; outcome configurable (ok / failure / raise)."""

    name = "fake"

    def __init__(self, *, ok: bool = True, raise_error: Exception | None = None):
        self._ok = ok
        self._raise = raise_error
        self.sent: list[PushMessage] = []

    async def send(self, message: PushMessage) -> ProviderResult:
        self.sent.append(message)
        if self._raise is not None:
            raise self._raise
        if self._ok:
            return ProviderResult(ok=True, provider=self.name, message_id="fake-1")
        return ProviderResult(
            ok=False,
            provider=self.name,
            error_kind=ProviderErrorKind.TRANSIENT,
            error_message="fake transport down",
        )


# --------------------------- seeding helpers ---------------------------


async def _seed_workspace(sm) -> dict:
    from oryx.core.models import Account, Workspace, WorkspaceMember

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"push+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Push WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id, account_id=account.id, role="owner"
            )
        )
        await session.commit()
        return {"workspace": workspace.id, "account": account.id}


async def _seed_device(sm, *, account_id, platform: str = "ios") -> uuid.UUID:
    from oryx.core.models import AlertDevice

    device_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            AlertDevice(
                id=device_id,
                account_id=account_id,
                platform=platform,
                push_token=f"tok-{device_id.hex}",
                app_version="0.1.0",
            )
        )
        await session.commit()
    return device_id


async def _set_push_preference(
    sm, *, account_id, type_: str = "system", frequency: str = "instant",
    quiet_hours: dict | None = None,
):
    from oryx.core.models import AlertPreference

    async with sm() as session:
        session.add(
            AlertPreference(
                account_id=account_id, type=type_, channel="push",
                frequency=frequency, quiet_hours=quiet_hours,
            )
        )
        await session.commit()


def _event(name: str = INTAKE_EVENT, *, workspace_id):
    from oryx.services.queue.bus import DomainEvent

    now = datetime.now(UTC)
    return DomainEvent(
        id=str(uuid.uuid4()),
        name=name,
        version=1,
        occurred_at=now,
        emitted_at=now,
        workspace_id=str(workspace_id),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={"itemId": "p-1"},
    )


def _dispatcher(sm, provider_factory):
    from oryx.services.activity.dispatcher import NotificationDispatcher

    return NotificationDispatcher(sm, push_provider_factory=provider_factory)


async def _logs(sm, account_id, channel: str):
    from oryx.core.models import AutomationLog

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(AutomationLog).where(
                        AutomationLog.account_id == account_id,
                        AutomationLog.channel == channel,
                    )
                )
            )
            .scalars()
            .all()
        )


async def _inbox_rows(sm, account_id):
    from oryx.core.models import ActivityInbox

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(ActivityInbox).where(ActivityInbox.account_id == account_id)
                )
            )
            .scalars()
            .all()
        )


def _window_around_now(*, start_offset_h: int, end_offset_h: int) -> dict:
    """A quiet_hours value whose window is positioned relative to real now.

    (-1, +1) always CONTAINS now — including when it wraps midnight, which the
    overnight branch handles; (+1, +2) never does. Deterministic without
    injecting a clock into the dispatcher.
    """
    now = datetime.now(UTC)
    return {
        "start": (now + timedelta(hours=start_offset_h)).strftime("%H:%M"),
        "end": (now + timedelta(hours=end_offset_h)).strftime("%H:%M"),
        "tz": "UTC",
    }


# --- Mandatory scenario 1: registration POSTs the token and it is stored ---


@pytest.mark.asyncio
async def test_device_registration_api_stores_token(app, sm) -> None:
    """POST /activity/devices with the exact RegisterAlertDeviceRequest shape
    the mobile client sends → a live alert_devices row holding the raw token;
    DELETE then disables it (the logout path)."""
    from oryx.core.models import AlertDevice

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"push+{uuid.uuid4().hex[:8]}@x.test",
            "password": "StrongPass123", "displayName": "Push",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        headers = {"Authorization": f"Bearer {signup.json()['data']['tokens']['accessToken']}"}

        token = f"raw-apns-{uuid.uuid4().hex}"
        res = await client.post(
            "/v1/activity/devices",
            json={"platform": "ios", "pushToken": token, "appVersion": "0.1.0"},
            headers=headers,
        )
        assert res.status_code == 200
        device = res.json()["data"]
        assert device["platform"] == "ios"
        device_id = uuid.UUID(device["id"])

        async with sm() as session:
            row = await session.get(AlertDevice, device_id)
        assert row is not None
        assert row.push_token == token
        assert row.disabled_at is None

        # Logout path: DELETE disables (soft) rather than deletes.
        res = await client.delete(f"/v1/activity/devices/{device_id}", headers=headers)
        assert res.status_code == 200
        async with sm() as session:
            row = await session.get(AlertDevice, device_id)
        assert row.disabled_at is not None


# --- Mandatory scenario 3: a time inside the quiet window suppresses push ---


@pytest.mark.asyncio
async def test_quiet_hours_inside_window_suppresses_push(sm) -> None:
    """Push enabled, device registered, but now is inside the account's quiet
    window: the provider is never called and — deliberately — NO push decision
    row is written (the §3.3 push vocabulary is push_sent/push_failed only).
    The in_app notification is untouched."""
    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])
    await _set_push_preference(
        sm, account_id=ids["account"],
        quiet_hours=_window_around_now(start_offset_h=-1, end_offset_h=1),
    )
    provider = FakePushProvider(ok=True)

    await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    assert provider.sent == []
    assert await _logs(sm, ids["account"], "push") == []
    assert len(await _inbox_rows(sm, ids["account"])) == 1  # in_app unaffected


@pytest.mark.asyncio
async def test_outside_quiet_hours_still_sends(sm) -> None:
    """The mirror case: a quiet window that does NOT contain now must not
    suppress anything."""
    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])
    await _set_push_preference(
        sm, account_id=ids["account"],
        quiet_hours=_window_around_now(start_offset_h=1, end_offset_h=2),
    )
    provider = FakePushProvider(ok=True)

    await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    assert len(provider.sent) == 1
    logs = await _logs(sm, ids["account"], "push")
    assert [log.action_taken for log in logs] == ["push_sent"]


# --- Mandatory scenario 5: a successful send logs push_sent ---


@pytest.mark.asyncio
async def test_push_sent_logged_via_fake_provider(sm) -> None:
    ids = await _seed_workspace(sm)
    device_id = await _seed_device(sm, account_id=ids["account"], platform="ios")
    provider = FakePushProvider(ok=True)
    seen_platforms: list[str] = []

    def factory(platform: str):
        seen_platforms.append(platform)
        return provider

    event = _event(workspace_id=ids["workspace"])
    await _dispatcher(sm, factory)(event)

    # The provider got the registered device's raw token and the event data.
    assert len(provider.sent) == 1
    message = provider.sent[0]
    assert message.token == f"tok-{device_id.hex}"
    assert message.title == "New item ingested"
    assert message.data["category"] == "system"
    assert seen_platforms == ["ios"]  # factory resolved per device platform

    # ONE push decision row, its own channel slot, linked to the feed row.
    inbox = await _inbox_rows(sm, ids["account"])
    logs = await _logs(sm, ids["account"], "push")
    assert len(logs) == 1
    assert logs[0].action_taken == "push_sent"
    assert logs[0].triggered_by_event_id == uuid.UUID(event.id)
    assert logs[0].activity_inbox_id == inbox[0].id


# --- Mandatory scenario 6: provider failure logs push_failed, no crash ---


@pytest.mark.asyncio
async def test_provider_failure_logs_push_failed_without_crashing(sm) -> None:
    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])
    provider = FakePushProvider(ok=False)

    await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    assert len(provider.sent) == 1  # it was attempted
    logs = await _logs(sm, ids["account"], "push")
    assert [log.action_taken for log in logs] == ["push_failed"]
    # The dispatch flow survived: in_app rows are intact.
    assert len(await _inbox_rows(sm, ids["account"])) == 1
    in_app = await _logs(sm, ids["account"], "in_app")
    assert [log.action_taken for log in in_app] == ["notification_created"]


@pytest.mark.asyncio
async def test_provider_exception_logs_push_failed_without_crashing(sm) -> None:
    """A provider that RAISES (not just returns ok=False) is contained the
    same way — the send loop maps it onto a failure result."""
    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])
    provider = FakePushProvider(raise_error=RuntimeError("boom"))

    await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    logs = await _logs(sm, ids["account"], "push")
    assert [log.action_taken for log in logs] == ["push_failed"]
    assert len(await _inbox_rows(sm, ids["account"])) == 1


# --- Mandatory scenario 7: no registered device → push_failed with a reason ---


@pytest.mark.asyncio
async def test_no_registered_device_logs_push_failed_with_reason(sm, caplog) -> None:
    """No alert_devices row at all: NOT a silent skip — a push_failed decision
    row lands, and the structured log carries the reason (automation_log's
    frozen §3.3 schema has no detail column, so the reason lives in the log
    line)."""
    ids = await _seed_workspace(sm)
    provider = FakePushProvider(ok=True)

    with caplog.at_level(logging.WARNING, logger="oryx.services.activity.dispatcher"):
        await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    assert provider.sent == []  # nothing to send to
    logs = await _logs(sm, ids["account"], "push")
    assert [log.action_taken for log in logs] == ["push_failed"]
    reasons = [getattr(r, "reason", None) for r in caplog.records]
    assert "no_registered_device" in reasons


# --- Mandatory scenario 8: inbox+log genuinely decoupled from the push step ---


@pytest.mark.asyncio
async def test_inbox_and_log_survive_push_step_total_failure(sm) -> None:
    """The push step fails ENTIRELY (the factory itself blows up before any
    provider handling) — the already-committed inbox row and its
    notification_created log row must stand. Proves the decoupling is real:
    the push step runs after the in_app transaction committed, so no push
    failure can roll the notification back."""

    def exploding_factory(_platform: str):
        raise RuntimeError("push infrastructure completely broken")

    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])

    # Must not raise despite the push step crashing wholesale.
    await _dispatcher(sm, exploding_factory)(_event(workspace_id=ids["workspace"]))

    inbox = await _inbox_rows(sm, ids["account"])
    assert len(inbox) == 1
    in_app = await _logs(sm, ids["account"], "in_app")
    assert [log.action_taken for log in in_app] == ["notification_created"]
    assert in_app[0].activity_inbox_id == inbox[0].id


# --- Mandatory scenario 9: digest rows do NOT trigger push (Wave C boundary) ---


@pytest.mark.asyncio
async def test_digest_rows_do_not_trigger_push(sm, monkeypatch) -> None:
    """DigestWorker was deliberately NOT wired to push this wave. A digest
    tick that really produces a bundle row must involve no provider call and
    write no push decision rows — with the provider factory globally patched
    to a spy, so ANY push attempt from the digest path would be caught."""
    from oryx.core.models import Account, ActivityInbox, AlertPreference, Profile
    from oryx.services.activity import dispatcher as dispatcher_module
    from oryx.services.activity.digest import DigestWorker

    provider = FakePushProvider(ok=True)
    monkeypatch.setattr(
        dispatcher_module, "get_push_provider", lambda _p: provider
    )

    created = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    account_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            Account(
                id=account_id,
                email=f"push+{account_id.hex[:8]}@oryx.test",
                password_hash="x",
                password_changed_at=created,
                created_at=created,
                status="active",
            )
        )
        await session.flush()
        session.add(Profile(account_id=account_id, display_name="D", timezone="UTC"))
        session.add(
            AlertPreference(
                account_id=account_id, type="system", channel="in_app",
                frequency="daily",
            )
        )
        # A push-channel pref AND a registered-device-free account would both
        # allow push if anything wired it — make push explicitly enabled so
        # the boundary (not a preference) is what's being proven.
        session.add(
            AlertPreference(
                account_id=account_id, type="system", channel="push",
                frequency="instant",
            )
        )
        session.add(
            ActivityInbox(
                id=uuid.uuid4(), account_id=account_id, workspace_id=None,
                type="system", severity="info", title="Bundled item", body=None,
                data={}, created_at=datetime(2026, 7, 2, 12, 0, tzinfo=UTC),
            )
        )
        await session.commit()

    # 2026-07-03 09:00 UTC — past the 08:00 UTC send point: the digest fires.
    await DigestWorker(sm).tick(now=datetime(2026, 7, 3, 9, 0, tzinfo=UTC))

    async with sm() as session:
        digests = (
            (
                await session.execute(
                    select(ActivityInbox).where(
                        ActivityInbox.account_id == account_id,
                        ActivityInbox.type == "daily_digest",
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(digests) == 1  # the digest genuinely happened...
    assert provider.sent == []  # ...and no push provider was ever called
    assert await _logs(sm, account_id, "push") == []  # no push decision rows


# --- Channel independence: in_app suppressed, push still delivers ---


@pytest.mark.asyncio
async def test_push_fires_even_when_in_app_suppressed(sm) -> None:
    """The channels are independent decisions (§4.1 step 3 'separately
    check'): in_app 'off' suppresses the feed row, but an enabled push pref
    still delivers — with activity_inbox_id=None since no feed row exists."""
    from oryx.core.models import AlertPreference

    ids = await _seed_workspace(sm)
    await _seed_device(sm, account_id=ids["account"])
    async with sm() as session:
        session.add(
            AlertPreference(
                account_id=ids["account"], type="system", channel="in_app",
                frequency="off",
            )
        )
        await session.commit()
    provider = FakePushProvider(ok=True)

    await _dispatcher(sm, lambda _p: provider)(_event(workspace_id=ids["workspace"]))

    assert await _inbox_rows(sm, ids["account"]) == []
    assert len(provider.sent) == 1
    logs = await _logs(sm, ids["account"], "push")
    assert [log.action_taken for log in logs] == ["push_sent"]
    assert logs[0].activity_inbox_id is None
