"""Digest email delivery — DigestWorker's own email step.

Closes the former §4.2 "emailed digests are out of scope" carve-out.
DigestWorker delivers digest email directly (see its module docstring for why
NotificationDispatcher's CATALOG/event-bus/workspace-fan-out machinery is the
wrong vehicle for an account-scoped bundle): after the bundle + digest_runs
transaction commits, it reads the (account, category, channel='email')
alert_preferences row, evaluates the same channel-agnostic is_quiet_now,
and calls get_email_provider() with template='digest' — reusing the exact
building blocks NotificationDispatcher's real-time email step uses, injected
here via DigestWorker's own email_provider_factory seam (mirrors
test_email_delivery.py's FakeEmailProvider pattern; no monkeypatching needed
since the factory is a constructor param, same as NotificationDispatcher).

Named scenarios:
  1. a real bundle renders a real digest email  test_real_digest_bundle_produces_rendered_email
  2. email pref 'off' sends nothing             test_email_disabled_preference_sends_no_email
  3. quiet hours suppress the email              test_quiet_hours_suppresses_digest_email
  4. outside quiet hours still sends             test_outside_quiet_hours_still_sends_digest_email
  5. double tick in one window emails once       test_double_tick_same_window_emails_once
  6. provider failure never undoes the digest    test_email_provider_failure_does_not_regress_digest_row
  7. in-app/digest-run rows unaffected by email   test_digest_rows_and_runs_unaffected_by_email_step
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
from oryx.services.activity.providers.email.rendering import render

pytestmark = pytest.mark.requires_db


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


async def _seed_account(
    sm,
    *,
    created_at: datetime,
    in_app_frequency: str = "daily",
    email_frequency: str | None = "instant",
    category: str = "system",
    quiet_hours: dict | None = None,
    timezone: str = "UTC",
) -> uuid.UUID:
    """Account + profile + in_app digest-cadence pref (+ optional email pref).

    `email_frequency=None` seeds no email-channel row at all — the default-
    enabled ('instant') path, same convention preferences.py documents for a
    missing row on every other channel.
    """
    from oryx.core.models import Account, AlertPreference, Profile

    account_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            Account(
                id=account_id,
                email=f"digest-mail+{account_id.hex[:8]}@oryx.test",
                password_hash="x",
                password_changed_at=created_at,
                created_at=created_at,
                status="active",
            )
        )
        await session.flush()
        session.add(
            Profile(account_id=account_id, display_name="Digest", timezone=timezone)
        )
        session.add(
            AlertPreference(
                account_id=account_id, type=category, channel="in_app",
                frequency=in_app_frequency,
            )
        )
        if email_frequency is not None:
            session.add(
                AlertPreference(
                    account_id=account_id, type=category, channel="email",
                    frequency=email_frequency, quiet_hours=quiet_hours,
                )
            )
        await session.commit()
    return account_id


async def _seed_inbox_row(
    sm, *, account_id: uuid.UUID, created_at: datetime,
    category: str = "system", title: str = "Seeded item", severity: str = "info",
) -> uuid.UUID:
    from oryx.core.models import ActivityInbox

    row_id = uuid.uuid4()
    async with sm() as session:
        session.add(
            ActivityInbox(
                id=row_id, account_id=account_id, workspace_id=None,
                type=category, severity=severity, title=title, body=None,
                data={}, created_at=created_at,
            )
        )
        await session.commit()
    return row_id


async def _digest_rows(sm, account_id: uuid.UUID):
    from oryx.core.models import ActivityInbox

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(ActivityInbox).where(
                        ActivityInbox.account_id == account_id,
                        ActivityInbox.type.in_(("daily_digest", "weekly_digest")),
                    ).order_by(ActivityInbox.created_at)
                )
            )
            .scalars()
            .all()
        )


async def _run_rows(sm, account_id: uuid.UUID):
    from oryx.core.models import DigestRun

    async with sm() as session:
        return (
            (
                await session.execute(
                    select(DigestRun).where(DigestRun.account_id == account_id)
                )
            )
            .scalars()
            .all()
        )


def _worker(sm, provider):
    from oryx.services.activity.digest import DigestWorker

    return DigestWorker(sm, email_provider_factory=lambda: provider)


def _window_around_now(*, start_offset_h: int, end_offset_h: int) -> dict:
    now = datetime.now(UTC)
    return {
        "start": (now + timedelta(hours=start_offset_h)).strftime("%H:%M"),
        "end": (now + timedelta(hours=end_offset_h)).strftime("%H:%M"),
        "tz": "UTC",
    }


# --- Scenario 1: a real bundle produces a real rendered email ---


@pytest.mark.asyncio
async def test_real_digest_bundle_produces_rendered_email(sm) -> None:
    """Three real inbox rows bundle into a real daily digest, and the digest
    email step sends one message with template='digest' whose rendered
    subject/body (via the real rendering.render(), not a mock) reflect the
    real bundle content — count, category, and highlighted titles."""
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
    )
    for i in range(3):
        await _seed_inbox_row(
            sm, account_id=account, title=f"item-{i}",
            created_at=datetime(2026, 7, 5, 10 + i, 0, tzinfo=UTC),
        )
    provider = FakeEmailProvider(ok=True)

    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    digests = await _digest_rows(sm, account)
    assert len(digests) == 1
    assert len(provider.sent) == 1
    message = provider.sent[0]
    assert message.template == "digest"
    assert message.variables["category"] == "system"
    assert message.variables["frequency"] == "daily"
    assert message.variables["count"] == "3"
    assert "item-0" in message.variables["highlights"]

    subject, body = render(message)
    assert "daily digest" in subject.lower()
    assert digests[0].title in body
    assert "item-0" in body


# --- Scenario 2: email preference 'off' sends nothing ---


@pytest.mark.asyncio
async def test_email_disabled_preference_sends_no_email(sm) -> None:
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
        email_frequency="off",
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    provider = FakeEmailProvider(ok=True)

    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    assert len(await _digest_rows(sm, account)) == 1  # in-app digest unaffected
    assert provider.sent == []


# --- Scenario 3: quiet hours suppress the digest email ---


@pytest.mark.asyncio
async def test_quiet_hours_suppresses_digest_email(sm) -> None:
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
        quiet_hours=_window_around_now(start_offset_h=-1, end_offset_h=1),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    provider = FakeEmailProvider(ok=True)

    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    assert provider.sent == []
    assert len(await _digest_rows(sm, account)) == 1  # digest itself still fired


# --- Scenario 4: outside quiet hours, email still sends ---


@pytest.mark.asyncio
async def test_outside_quiet_hours_still_sends_digest_email(sm) -> None:
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
        quiet_hours=_window_around_now(start_offset_h=1, end_offset_h=2),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    provider = FakeEmailProvider(ok=True)

    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    assert len(provider.sent) == 1


# --- Scenario 5: idempotency — a double tick inside one window emails once ---


@pytest.mark.asyncio
async def test_double_tick_same_window_emails_once(sm) -> None:
    """Two ticks inside the same daily window: the digest_runs UNIQUE
    constraint (not a new automation_log-style slot) is what makes the second
    tick a pure no-op before it ever reaches the email step — same
    once-only guarantee the alert path gets from automation_log, applied via
    the mechanism that actually exists for digests."""
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    provider = FakeEmailProvider(ok=True)
    worker = _worker(sm, provider)

    await worker.tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))
    await worker.tick(now=datetime(2026, 7, 6, 8, 31, tzinfo=UTC))

    assert len(await _digest_rows(sm, account)) == 1
    assert len(await _run_rows(sm, account)) == 1
    assert len(provider.sent) == 1


# --- Scenario 6: a failing/raising provider never regresses the digest row ---


@pytest.mark.asyncio
async def test_email_provider_failure_does_not_regress_digest_row(sm) -> None:
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 5, 0, 0, tzinfo=UTC),
    )
    await _seed_inbox_row(
        sm, account_id=account, created_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    )
    provider = FakeEmailProvider(raise_error=RuntimeError("smtp exploded"))

    # Must not raise despite the email step blowing up entirely.
    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    digests = await _digest_rows(sm, account)
    assert len(digests) == 1
    assert digests[0].data["count"] == 1
    assert len(await _run_rows(sm, account)) == 1
    assert len(provider.sent) == 1  # it was attempted


# --- Scenario 7: existing in-app/digest_runs behavior is unregressed ---


@pytest.mark.asyncio
async def test_digest_rows_and_runs_unaffected_by_email_step(sm) -> None:
    """The bundling engine's own output (bundled_ids, count, DigestRun window)
    is byte-identical to the pre-email-wave shape regardless of what the email
    step does — proven here with an email provider that raises on every call,
    the harshest case."""
    account = await _seed_account(
        sm, created_at=datetime(2026, 7, 4, 0, 0, tzinfo=UTC),
    )
    ids = {
        str(
            await _seed_inbox_row(
                sm, account_id=account, title=f"row-{i}",
                created_at=datetime(2026, 7, 5, 10 + i, 0, tzinfo=UTC),
            )
        )
        for i in range(3)
    }
    provider = FakeEmailProvider(raise_error=RuntimeError("boom"))

    await _worker(sm, provider).tick(now=datetime(2026, 7, 6, 8, 30, tzinfo=UTC))

    digests = await _digest_rows(sm, account)
    assert len(digests) == 1
    assert set(digests[0].data["bundled_ids"]) == ids
    assert digests[0].data["count"] == 3
    runs = await _run_rows(sm, account)
    assert len(runs) == 1
    assert runs[0].frequency == "daily"
    assert runs[0].activity_type == "system"
