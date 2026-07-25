"""BillingService.apply_webhook_event: subscription state transitions must
only promote Workspace.plan on a genuine confirmed-active status, never on
subscription creation / AFA-pending states alone."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


async def _seed_workspace(sm) -> uuid.UUID:
    from oryx.core.models import Account, Workspace

    now = datetime.now(UTC)
    async with sm() as session:
        account = Account(
            id=uuid.uuid4(),
            email=f"billing+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        workspace = Workspace(
            id=uuid.uuid4(), name="Billing WS", owner_account_id=account.id
        )
        session.add(workspace)
        await session.commit()
        return workspace.id


def _sub_id() -> str:
    """Unique per call — this suite has no transaction-rollback isolation
    (see conftest.py), so a hardcoded provider_subscription_id would collide
    with a stale row from an earlier run of the same test and silently
    promote a DIFFERENT (old) workspace instead of this test's own."""
    return f"sub_{uuid.uuid4().hex[:12]}"


async def _get_plan(sm, workspace_id: uuid.UUID) -> str:
    from oryx.core.models import Workspace

    async with sm() as session:
        result = await session.execute(
            select(Workspace.plan).where(Workspace.id == workspace_id)
        )
        return result.scalar_one()


async def test_stripe_creation_event_never_promotes_plan(sm) -> None:
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)
    assert await _get_plan(sm, workspace_id) == "glimpse"  # new default
    sub_id = _sub_id()

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id,
            provider="stripe",
            provider_subscription_id=sub_id,
            event_type="customer.subscription.created",
            raw={},
            plan="vision",
            currency="USD",
        )
        await session.commit()

    assert status.value == "pending"
    # Creation alone must never promote the workspace, even though a target
    # tier ("vision") was already known from the vendor metadata.
    assert await _get_plan(sm, workspace_id) == "glimpse"


async def test_stripe_invoice_paid_promotes_plan_to_known_tier(sm) -> None:
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)
    sub_id = _sub_id()

    async with sm() as session:
        svc = BillingService(session)
        await svc.apply_webhook_event(
            workspace_id=workspace_id,
            provider="stripe",
            provider_subscription_id=sub_id,
            event_type="customer.subscription.created",
            raw={},
            plan="focus",
            currency="USD",
        )
        await session.commit()

    assert await _get_plan(sm, workspace_id) == "glimpse"

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id,
            provider="stripe",
            provider_subscription_id=sub_id,
            event_type="invoice.paid",
            raw={},
        )
        await session.commit()

    assert status.value == "active"
    assert await _get_plan(sm, workspace_id) == "focus"


async def test_stripe_payment_failed_moves_to_past_due_without_reverting_plan(sm) -> None:
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)
    sub_id = _sub_id()

    async with sm() as session:
        svc = BillingService(session)
        await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="stripe",
            provider_subscription_id=sub_id, event_type="invoice.paid",
            raw={}, plan="clarity", currency="USD",
        )
        await session.commit()
    assert await _get_plan(sm, workspace_id) == "clarity"

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="stripe",
            provider_subscription_id=sub_id,
            event_type="invoice.payment_failed", raw={},
        )
        await session.commit()

    assert status.value == "past_due"
    # PAST_DUE is not a promotion event; the workspace keeps its last-known
    # active tier rather than being silently reverted.
    assert await _get_plan(sm, workspace_id) == "clarity"


async def test_razorpay_authenticated_then_activated_only_promotes_on_activation(sm) -> None:
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)
    sub_id = _sub_id()

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="razorpay",
            provider_subscription_id=sub_id,
            event_type="subscription.authenticated", raw={},
            plan="vision", currency="INR",
        )
        await session.commit()
    assert status.value == "pending"
    assert await _get_plan(sm, workspace_id) == "glimpse"

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="razorpay",
            provider_subscription_id=sub_id,
            event_type="subscription.activated", raw={},
        )
        await session.commit()
    assert status.value == "active"
    assert await _get_plan(sm, workspace_id) == "vision"


async def test_razorpay_halted_does_not_promote_and_is_recorded_past_due(sm) -> None:
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="razorpay",
            provider_subscription_id=_sub_id(),
            event_type="subscription.halted", raw={},
            plan="focus", currency="INR",
        )
        await session.commit()

    assert status.value == "past_due"
    assert await _get_plan(sm, workspace_id) == "glimpse"


async def test_unknown_tier_never_guessed_even_on_active_event(sm) -> None:
    """A subscription whose tier was never communicated (no plan_ref on any
    event seen so far) must not promote the workspace even on a confirmed
    ACTIVE transition — guessing a tier is worse than enforcing none yet."""
    from oryx.services.billing.service import BillingService

    workspace_id = await _seed_workspace(sm)

    async with sm() as session:
        svc = BillingService(session)
        status = await svc.apply_webhook_event(
            workspace_id=workspace_id, provider="stripe",
            provider_subscription_id=_sub_id(),
            event_type="invoice.paid", raw={}, currency="USD",
            # plan intentionally omitted
        )
        await session.commit()

    assert status.value == "active"
    assert await _get_plan(sm, workspace_id) == "glimpse"
