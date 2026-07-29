"""Email alert delivery — dispatcher email step (instant alerts only).

Drives NotificationDispatcher the same way test_push_delivery.py does
(construct a DomainEvent, call the handler, assert on committed rows), with a
FAKE email provider injected through the dispatcher's email_provider_factory
seam — the real SendGrid/SMTP wire code has its own unit coverage in
tests/unit/test_email_providers.py.

Scope boundary under test throughout: this file covers INSTANT (single
real-time CATALOG event) email alerts only, dispatched by
NotificationDispatcher. Emailed DIGESTS (bundled summaries) are a separate
former §4.2 carve-out, now closed — but delivered by DigestWorker itself, not
by NotificationDispatcher (see digest.py's module docstring for why the
dispatcher's workspace/CATALOG fan-out doesn't fit an account-scoped bundle);
that coverage lives in test_digest_email.py, not here.

The mandatory scenarios covered here:
  1. enabled pref sends + logs email_sent   test_email_sent_logged_via_fake_provider
  2. provider failure logs email_failed     test_provider_failure_logs_email_failed_without_crashing
  3. quiet window suppresses email          test_quiet_hours_inside_window_suppresses_email
  4. inbox+log decoupled from email step    test_inbox_and_log_survive_email_step_total_failure
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from oryx.services.activity.providers.email.base import (
    EmailMessage,
    ProviderErrorKind,
    ProviderResult,
)

pytestmark = pytest.mark.requires_db

INTAKE_EVENT = "intake.item.received"  # category 'system'


class FakeEmailProvider:
    """Records every send; outcome configurable (ok / failure / raise)."""

    name = "fake"

    def __init__(self, *, ok: bool = True, raise_error: Exception | None = None):
        self._ok = ok
        self._raise = raise_error
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> ProviderResult:
        self.sent.append(message)
        if self._raise is not None:
            raise self._raise
        if self._ok:
            return ProviderResult(ok=True, provider=self.name, message_id="fake-1")
        return ProviderResult(
            ok=False,
            provider=self.name,
            error_kind=ProviderErrorKind.TRANSIENT,
            error_message="fake smtp down",
        )


# --------------------------- seeding helpers ---------------------------


async def _seed_workspace(sm) -> dict:
    from oryx.core.models import Account, Workspace, WorkspaceMember

    now = datetime.now(UTC)
    email = f"mail+{uuid.uuid4().hex[:8]}@oryx.test"
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=email,
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Mail WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id, account_id=account.id, role="owner"
            )
        )
        await session.commit()
        return {"workspace": workspace.id, "account": account.id, "email": email}


async def _set_email_preference(
    sm, *, account_id, type_: str = "system", frequency: str = "instant",
    quiet_hours: dict | None = None,
):
    from oryx.core.models import AlertPreference

    async with sm() as session:
        session.add(
            AlertPreference(
                account_id=account_id, type=type_, channel="email",
                frequency=frequency, quiet_hours=quiet_hours,
            )
        )
        await session.commit()


def _event(
    name: str = INTAKE_EVENT, *, workspace_id, event_id: uuid.UUID | None = None
):
    from oryx.services.queue.bus import DomainEvent

    now = datetime.now(UTC)
    return DomainEvent(
        id=str(event_id or uuid.uuid4()),
        name=name,
        version=1,
        occurred_at=now,
        emitted_at=now,
        workspace_id=str(workspace_id),
        actor_kind="system",
        actor_id=None,
        correlation_id=str(uuid.uuid4()),
        causation_id=None,
        payload={"itemId": "m-1"},
    )


def _dispatcher(sm, email_factory):
    from oryx.services.activity.dispatcher import NotificationDispatcher

    return NotificationDispatcher(sm, email_provider_factory=email_factory)


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
    """A quiet_hours value positioned relative to real now — (-1, +1) always
    CONTAINS now (the overnight branch handles a midnight wrap); (+1, +2)
    never does. Same trick as test_push_delivery.py."""
    now = datetime.now(UTC)
    return {
        "start": (now + timedelta(hours=start_offset_h)).strftime("%H:%M"),
        "end": (now + timedelta(hours=end_offset_h)).strftime("%H:%M"),
        "tz": "UTC",
    }


# --- Mandatory scenario 1: enabled email preference sends + logs email_sent ---


@pytest.mark.asyncio
async def test_email_sent_logged_via_fake_provider(sm) -> None:
    """An explicit 'instant' email preference: the provider receives ONE
    message addressed to the account's own signup address (accounts.email —
    the same field the password-forgot flow keys on), and one channel='email'
    decision row lands, linked to the feed row."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])
    provider = FakeEmailProvider(ok=True)

    event = _event(workspace_id=ids["workspace"])
    await _dispatcher(sm, lambda: provider)(event)

    assert len(provider.sent) == 1
    message = provider.sent[0]
    assert message.to == ids["email"]  # the signup address, nothing configured
    assert message.template == "alert"
    assert message.variables["title"] == "New item ingested"
    assert message.variables["category"] == "system"
    assert message.variables["event_type"] == INTAKE_EVENT

    inbox = await _inbox_rows(sm, ids["account"])
    logs = await _logs(sm, ids["account"], "email")
    assert len(logs) == 1
    assert logs[0].action_taken == "email_sent"
    assert logs[0].channel == "email"
    assert logs[0].triggered_by_event_id == uuid.UUID(event.id)
    assert logs[0].activity_inbox_id == inbox[0].id


# --- Mandatory scenario 2: provider failure logs email_failed, no crash ---


@pytest.mark.asyncio
async def test_provider_failure_logs_email_failed_without_crashing(sm) -> None:
    """Mirrors push's decoupling proof: a failing provider yields an
    email_failed decision row while the dispatch flow — the inbox row and its
    in_app decision log — survives untouched."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])
    provider = FakeEmailProvider(ok=False)

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    assert len(provider.sent) == 1  # it was attempted
    logs = await _logs(sm, ids["account"], "email")
    assert [log.action_taken for log in logs] == ["email_failed"]
    # The dispatch flow survived: in_app rows are intact.
    assert len(await _inbox_rows(sm, ids["account"])) == 1
    in_app = await _logs(sm, ids["account"], "in_app")
    assert [log.action_taken for log in in_app] == ["notification_created"]


@pytest.mark.asyncio
async def test_provider_exception_logs_email_failed_without_crashing(sm) -> None:
    """A provider that RAISES (not just returns ok=False) is contained the
    same way — the send is mapped onto a failure result."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])
    provider = FakeEmailProvider(raise_error=RuntimeError("boom"))

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    logs = await _logs(sm, ids["account"], "email")
    assert [log.action_taken for log in logs] == ["email_failed"]
    assert len(await _inbox_rows(sm, ids["account"])) == 1


# --- Detail persistence (migration 0024): the failure reason lives ON the row ---


@pytest.mark.asyncio
async def test_email_failed_provider_error_persists_reason_in_detail(sm) -> None:
    """Same contract as push: an email failure persists the provider's error
    string as the row's detail, so the Automation Hub can show WHY; a success
    stays null."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])
    provider = FakeEmailProvider(ok=False)  # returns "fake smtp down"

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    logs = await _logs(sm, ids["account"], "email")
    assert [(log.action_taken, log.detail) for log in logs] == [
        ("email_failed", "fake: fake smtp down")
    ]


# --- Mandatory scenario 3: quiet hours suppress email (is_quiet_now reused) ---


@pytest.mark.asyncio
async def test_quiet_hours_inside_window_suppresses_email(sm) -> None:
    """Email enabled but now is inside the email-channel row's quiet window:
    the provider is NEVER called and the skip is recorded as
    email_suppressed_quiet_hours — proof the channel-agnostic is_quiet_now
    actually fires for email, not just push. The in_app notification is
    untouched, and redelivery adds nothing (slot idempotency)."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(
        sm, account_id=ids["account"],
        quiet_hours=_window_around_now(start_offset_h=-1, end_offset_h=1),
    )
    provider = FakeEmailProvider(ok=True)
    event_id = uuid.uuid4()
    dispatcher = _dispatcher(sm, lambda: provider)

    await dispatcher(_event(workspace_id=ids["workspace"], event_id=event_id))
    await dispatcher(_event(workspace_id=ids["workspace"], event_id=event_id))

    assert provider.sent == []
    logs = await _logs(sm, ids["account"], "email")
    assert len(logs) == 1  # exactly one, redelivery included
    assert logs[0].action_taken == "email_suppressed_quiet_hours"
    inbox = await _inbox_rows(sm, ids["account"])
    assert len(inbox) == 1  # in_app unaffected
    assert logs[0].activity_inbox_id == inbox[0].id


@pytest.mark.asyncio
async def test_outside_quiet_hours_still_sends_email(sm) -> None:
    """The mirror case: a quiet window that does NOT contain now must not
    suppress anything."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(
        sm, account_id=ids["account"],
        quiet_hours=_window_around_now(start_offset_h=1, end_offset_h=2),
    )
    provider = FakeEmailProvider(ok=True)

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    assert len(provider.sent) == 1
    logs = await _logs(sm, ids["account"], "email")
    assert [log.action_taken for log in logs] == ["email_sent"]


# --- Mandatory scenario 4: inbox+log genuinely decoupled from the email step ---


@pytest.mark.asyncio
async def test_inbox_and_log_survive_email_step_total_failure(sm) -> None:
    """The email step fails ENTIRELY (the factory itself blows up before any
    provider handling) — the already-committed inbox row and its
    notification_created log row must stand. Same standard as push: the email
    step runs after the in_app transaction committed, so no email failure can
    roll the notification back."""

    def exploding_factory():
        raise RuntimeError("email infrastructure completely broken")

    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])

    # Must not raise despite the email step crashing wholesale.
    await _dispatcher(sm, exploding_factory)(_event(workspace_id=ids["workspace"]))

    inbox = await _inbox_rows(sm, ids["account"])
    assert len(inbox) == 1
    in_app = await _logs(sm, ids["account"], "in_app")
    assert [log.action_taken for log in in_app] == ["notification_created"]
    assert in_app[0].activity_inbox_id == inbox[0].id


# --- Channel boundaries beyond the mandatory four ---


@pytest.mark.asyncio
async def test_email_disabled_preference_writes_no_email_decision(sm) -> None:
    """An explicit email-channel 'off': no provider call, no email decision
    row at all — and it must not suppress the in_app notification (same
    two-sided independence the push slot proved)."""
    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"], frequency="off")
    provider = FakeEmailProvider(ok=True)

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    assert provider.sent == []
    assert await _logs(sm, ids["account"], "email") == []
    assert len(await _inbox_rows(sm, ids["account"])) == 1


@pytest.mark.asyncio
async def test_ff_email_delivery_enabled_by_default(sm) -> None:
    """Migration 0022 flips ff_email_delivery's global default ON — this wave
    ships everything the flag stands for, the flag gates no client surface
    yet, and real sending stays double-gated behind EMAIL_PROVIDER (default
    log_only) plus per-account preferences."""
    import os

    from httpx import ASGITransport, AsyncClient

    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        signup = await client.post("/v1/auth/signup", json={
            "email": f"mail+{uuid.uuid4().hex[:8]}@x.test",
            "password": "StrongPass123", "displayName": "Mail",
            "deviceId": "d", "deviceLabel": "l", "devicePlatform": "ios",
        })
        headers = {"Authorization": f"Bearer {signup.json()['data']['tokens']['accessToken']}"}
        flags = (
            await client.get("/v1/feature-flags", headers=headers)
        ).json()["data"]
        assert flags["ff_email_delivery"] is True


@pytest.mark.asyncio
async def test_email_fires_even_when_in_app_suppressed(sm) -> None:
    """Channel independence in the other direction: in_app 'off' suppresses
    the feed row, but an enabled email pref still delivers — with
    activity_inbox_id=None since no feed row exists."""
    from oryx.core.models import AlertPreference

    ids = await _seed_workspace(sm)
    await _set_email_preference(sm, account_id=ids["account"])
    async with sm() as session:
        session.add(
            AlertPreference(
                account_id=ids["account"], type="system", channel="in_app",
                frequency="off",
            )
        )
        await session.commit()
    provider = FakeEmailProvider(ok=True)

    await _dispatcher(sm, lambda: provider)(_event(workspace_id=ids["workspace"]))

    assert await _inbox_rows(sm, ids["account"]) == []
    assert len(provider.sent) == 1
    logs = await _logs(sm, ids["account"], "email")
    assert [log.action_taken for log in logs] == ["email_sent"]
    assert logs[0].activity_inbox_id is None
